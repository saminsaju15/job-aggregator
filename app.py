import streamlit as st
import sqlite3
import pandas as pd

# Page config
st.set_page_config(
    page_title="AI Job Aggregator",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .job-card {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 5px solid #0052cc;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        color: #333;
    }
    
    .job-card.reach {
        border-left: 5px solid #ff9900;
    }
    
    .job-title {
        font-size: 20px;
        font-weight: bold;
        color: #1e1e1e;
        margin-bottom: 5px;
    }
    
    .company-name {
        font-size: 16px;
        color: #555;
        font-weight: 600;
        margin-bottom: 15px;
    }
    
    .metadata {
        display: flex;
        gap: 15px;
        margin-bottom: 15px;
        font-size: 14px;
        color: #666;
    }
    
    .badge {
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        display: inline-block;
    }
    
    .badge-strong {
        background-color: #e3fcef;
        color: #006644;
    }
    
    .badge-reach {
        background-color: #fff0b3;
        color: #ff9900;
    }
    
    .justification {
        background-color: #eef2ff;
        padding: 15px;
        border-radius: 8px;
        font-style: italic;
        color: #2c3e50;
        margin-top: 15px;
        border-left: 3px solid #6366f1;
    }
    
    a.apply-btn {
        display: inline-block;
        margin-top: 15px;
        padding: 8px 15px;
        background-color: #0052cc;
        color: white !important;
        text-decoration: none;
        border-radius: 5px;
        font-weight: bold;
        transition: background-color 0.3s;
    }
    
    a.apply-btn:hover {
        background-color: #003d99;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load_data():
    try:
        conn = sqlite3.connect("job_tracker.db")
        # Only fetch Strong Fit and Reach
        query = "SELECT * FROM reviewed_jobs WHERE fit_category IN ('Strong Fit', 'Reach') ORDER BY timestamp DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except sqlite3.OperationalError:
        # DB might not exist yet
        return pd.DataFrame()

def main():
    st.title("💼 AI-Powered Job Aggregator")
    st.markdown("Automated sourcing and evaluation for Senior Business Process Analyst roles using Gemini AI.")
    st.markdown("---")
    
    df = load_data()
    
    if df.empty:
        st.info("No jobs found in the database. Please run the `main_scraper.py` script to fetch and evaluate jobs.")
        return
        
    # Sidebar Filters
    st.sidebar.header("Filters")
    
    # Category Filter
    categories = df['fit_category'].unique().tolist()
    selected_categories = st.sidebar.multiselect("Fit Category", categories, default=categories)
    
    # Location Filter
    locations = sorted(df['location'].unique().tolist())
    selected_locations = st.sidebar.multiselect("Location", locations, default=locations)
    
    # Company Filter
    companies = sorted(df['company'].unique().tolist())
    selected_companies = st.sidebar.multiselect("Company", companies, default=companies)
    
    # Apply Filters
    filtered_df = df[
        (df['fit_category'].isin(selected_categories)) &
        (df['location'].isin(selected_locations)) &
        (df['company'].isin(selected_companies))
    ]
    
    st.subheader(f"Curated Opportunities ({len(filtered_df)})")
    
    # Display Job Cards
    for _, row in filtered_df.iterrows():
        cat_class = "reach" if row['fit_category'] == "Reach" else ""
        badge_class = "badge-reach" if row['fit_category'] == "Reach" else "badge-strong"
        
        apply_btn_html = f'<a href="{row["url"]}" target="_blank" class="apply-btn">Apply Now</a>' if row["url"] else ''
        
        card_html = f"""
        <div class="job-card {cat_class}">
            <div class="job-title">{row['title']}</div>
            <div class="company-name">{row['company']}</div>
            <div class="metadata">
                <span>📍 {row['location']}</span>
                <span>💰 {row['salary_info']}</span>
                <span class="badge {badge_class}">{row['fit_category']}</span>
                <span>🕒 {str(row['timestamp'])[:10]}</span>
            </div>
            
            <div class="justification">
                <strong>🤖 AI Evaluation:</strong><br>
                {row['justification']}
            </div>
            
            {apply_btn_html}
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
