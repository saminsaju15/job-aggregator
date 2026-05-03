import os
import sqlite3
import json
import time
import requests
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut

# Load environment variables
load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not RAPIDAPI_KEY or not GEMINI_API_KEY:
    print("Warning: Missing RAPIDAPI_KEY or GEMINI_API_KEY. Please check your .env file.")

# Initialize Gemini Client
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    gemini_client = None
    print(f"Failed to initialize Gemini client: {e}")

# Target coordinates for distance calculation
BERGENFIELD_COORDS = (40.9276, -73.9974) # Bergenfield, NJ
MAX_DISTANCE_MILES = 30.0

# Initialize Geocoder
geolocator = Nominatim(user_agent="job_aggregator_app")
location_cache = {}

class JobEvaluation(BaseModel):
    fit_category: str = Field(description="Must be exactly one of: 'Reject', 'Strong Fit', or 'Reach'")
    justification: str = Field(description="A 2-sentence justification for the categorization.")

def init_db():
    conn = sqlite3.connect("job_tracker.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviewed_jobs (
            job_id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            salary_info TEXT,
            fit_category TEXT,
            justification TEXT,
            url TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def is_job_reviewed(job_id: str) -> bool:
    conn = sqlite3.connect("job_tracker.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM reviewed_jobs WHERE job_id = ?", (job_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def save_job(job_id, title, company, location, salary_info, fit_category, justification, url):
    conn = sqlite3.connect("job_tracker.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reviewed_jobs (job_id, title, company, location, salary_info, fit_category, justification, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (job_id, title, company, location, salary_info, fit_category, justification, url))
    conn.commit()
    conn.close()

def fetch_jobs_from_jsearch(query: str, num_pages: int = 1) -> List[Dict]:
    url = "https://jsearch.p.rapidapi.com/search"
    querystring = {"query": query, "page": "1", "num_pages": str(num_pages)}
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "jsearch.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
    except Exception as e:
        print(f"Error fetching jobs for query '{query}': {e}")
        return []

def is_within_radius(job_city: str, job_state: str) -> bool:
    if not job_city or not job_state:
        return False
        
    location_str = f"{job_city}, {job_state}"
    
    # NYC check - always valid
    if "New York" in job_city and "NY" in job_state:
        return True
        
    # Check cache
    if location_str in location_cache:
        coords = location_cache[location_str]
    else:
        try:
            # Geocode
            location = geolocator.geocode(location_str, timeout=5)
            if location:
                coords = (location.latitude, location.longitude)
                location_cache[location_str] = coords
            else:
                location_cache[location_str] = None
                return False
        except Exception as e:
            print(f"Geocoding error for {location_str}: {e}")
            return False
            
    if not coords:
        return False
        
    distance = geodesic(BERGENFIELD_COORDS, coords).miles
    return distance <= MAX_DISTANCE_MILES

def is_salary_acceptable(job_data: Dict) -> bool:
    # JSearch provides min and max salary
    min_salary = job_data.get('job_min_salary')
    max_salary = job_data.get('job_max_salary')
    
    # If missing, we keep it as requested
    if min_salary is None and max_salary is None:
        return True
        
    # Check if either min or max meets the threshold
    if min_salary is not None and min_salary >= 174000:
        return True
    if max_salary is not None and max_salary >= 174000:
        return True
        
    return False

def evaluate_job_with_gemini(job_description: str) -> Optional[JobEvaluation]:
    if not gemini_client:
        return None
        
    prompt = f"""
    You are an expert technical recruiter evaluating jobs for a candidate. The candidate is a Senior Business Process Analyst and Platform Lead with 7 years of experience delivering 0-to-1 enterprise builds across IT, HR, Finance, and Legal. They manage platforms serving 12,000+ users. Their expertise is in ServiceNow (ITSM, App Engine, HRSD, CMDB), Workday integrations, Power BI, and executive KPI governance. They are currently an MBA candidate.
    CRITICAL RULE: The candidate works in IT and platform architecture, but they are NOT a software developer or programmer, and they struggle with basic coding.

    Evaluate the following job description.
    - Reject: Automatically reject any role that requires writing production code, hands-on software engineering, passing coding tests, or junior-level (2-4 years) experience.
    - Strong Fit: Highly score roles emphasizing ServiceNow architecture, enterprise workflow leadership, AI-enabled service operations (Gen AI enablement), or process governance.
    - Reach: Roles like Product Manager at FAANG, MAANG, or major Banking/Financial institutions that might be challenging but rely heavily on platform strategy and stakeholder management rather than raw engineering.

    Job Description:
    {job_description[:5000]} # Limiting length to ensure within context window if necessary
    """
    
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': JobEvaluation,
                'temperature': 0.1
            },
        )
        
        result_json = json.loads(response.text)
        return JobEvaluation(**result_json)
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

def main():
    print("Initializing Database...")
    init_db()
    
    keywords = [
        "Business Analyst",
        "Process Analyst",
        "ServiceNow Process Manager",
        "ServiceNow Product",
        "Product Manager",
        "Process Manager",
        "Technical Program Manager"
    ]
    
    # Base locations to search in JSearch
    locations = ["New York, NY", "Bergenfield, NJ"]
    
    for loc in locations:
        for kw in keywords:
            query = f"{kw} in {loc}"
            print(f"\nSearching for: {query}")
            
            jobs = fetch_jobs_from_jsearch(query, num_pages=1)
            print(f"Found {len(jobs)} jobs for query.")
            
            for job in jobs:
                job_id = job.get('job_id')
                if not job_id:
                    continue
                    
                if is_job_reviewed(job_id):
                    continue
                
                # Pre-filters
                title = job.get('job_title', 'Unknown')
                company = job.get('employer_name', 'Unknown')
                city = job.get('job_city', '')
                state = job.get('job_state', '')
                location_str = f"{city}, {state}".strip(", ")
                
                if not is_within_radius(city, state):
                    print(f"  Skipping {title} at {company} - Location ({location_str}) outside 30mi radius.")
                    # Mark as reviewed so we don't keep evaluating it? Let's just skip so we don't spam db, or maybe we should save it as Reject. 
                    # For now, let's just save it as reject to prevent re-fetching and re-checking distance.
                    save_job(job_id, title, company, location_str, "N/A", "Reject", "Outside 30mi commute radius.", job.get('job_apply_link', ''))
                    continue
                    
                if not is_salary_acceptable(job):
                    print(f"  Skipping {title} at {company} - Salary below $174k threshold.")
                    save_job(job_id, title, company, location_str, "Below 174k", "Reject", "Salary below threshold.", job.get('job_apply_link', ''))
                    continue
                    
                desc = job.get('job_description')
                if not desc:
                    continue
                    
                print(f"  Evaluating {title} at {company} with Gemini...")
                evaluation = evaluate_job_with_gemini(desc)
                
                if evaluation:
                    fit_category = evaluation.fit_category
                    justification = evaluation.justification
                    
                    min_sal = job.get('job_min_salary')
                    max_sal = job.get('job_max_salary')
                    sal_info = "Not specified"
                    if min_sal or max_sal:
                        sal_info = f"${min_sal or '?'}/yr - ${max_sal or '?'}/yr"
                        
                    url = job.get('job_apply_link', '')
                    
                    print(f"  -> {fit_category}: {justification[:50]}...")
                    save_job(job_id, title, company, location_str, sal_info, fit_category, justification, url)
                    
                    # Sleep to avoid rate limits
                    time.sleep(2)

if __name__ == "__main__":
    main()
