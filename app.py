import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="AI Job Aggregator",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data(ttl=60)
def load_data():
    try:
        conn = sqlite3.connect("job_tracker.db")
        # Fetch only Strong Fit and Reach
        query = "SELECT * FROM reviewed_jobs WHERE fit_category IN ('Strong Fit', 'Reach') ORDER BY timestamp DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Ensure timestamp is datetime type for fallback
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # If posted_date exists (new db column), use it, otherwise fallback to timestamp
            if 'posted_date' in df.columns:
                df['posted_date'] = pd.to_datetime(df['posted_date'], errors='coerce')
                df['posted_date'] = df['posted_date'].fillna(df['timestamp'])
            else:
                df['posted_date'] = df['timestamp']
            
        return df
    except (sqlite3.OperationalError, pd.errors.DatabaseError):
        # DB might not exist yet or table is missing
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
    st.sidebar.header("Filter Results")
    
    # Time Filter
    time_options = {
        "All Time": None,
        "Last 24 Hours": 1,
        "Last 48 Hours": 2,
        "Last 7 Days": 7,
        "Last 10 Days": 10
    }
    selected_time = st.sidebar.selectbox("Date Posted", list(time_options.keys()))
    
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
    
    if time_options[selected_time] is not None:
        cutoff_date = datetime.now() - timedelta(days=time_options[selected_time])
        # Convert cutoff_date to UTC-aware to match JSearch timestamps
        import pytz
        cutoff_date = cutoff_date.replace(tzinfo=pytz.UTC)
        
        # Ensure df column is tz-aware for comparison
        if filtered_df['posted_date'].dt.tz is None:
            filtered_df['posted_date'] = filtered_df['posted_date'].dt.tz_localize('UTC')
            
        filtered_df = filtered_df[filtered_df['posted_date'] >= cutoff_date]
        
    st.sidebar.markdown("---")
    sort_by = st.sidebar.selectbox("Sort By", ["Date Posted (Newest First)", "Fit Category (Strong Fit First)"])
    
    if sort_by == "Date Posted (Newest First)":
        filtered_df = filtered_df.sort_values(by='posted_date', ascending=False)
    else:
        # Sort by fit category (Strong Fit first) then date
        filtered_df['cat_rank'] = filtered_df['fit_category'].map({"Strong Fit": 1, "Reach": 2})
        filtered_df = filtered_df.sort_values(by=['cat_rank', 'posted_date'], ascending=[True, False])
        filtered_df = filtered_df.drop(columns=['cat_rank'])
    
    st.subheader(f"Curated Opportunities ({len(filtered_df)})")
    
    if filtered_df.empty:
        st.warning("No jobs match your current filters.")
        return
    
    # Display cleaner, native Streamlit UI
    faang_companies = ["meta", "facebook", "apple", "amazon", "netflix", "google", "alphabet", "microsoft"]
    
    for _, row in filtered_df.iterrows():
        cat_emoji = "🟢" if row['fit_category'] == "Strong Fit" else "🟡"
        
        # Check if company is FAANG/MAANG
        is_faang = any(faang in str(row['company']).lower() for faang in faang_companies)
        faang_badge = " 🚀 **[FAANG/MAANG TARGET]**" if is_faang else ""
        
        with st.expander(f"{cat_emoji} {row['title']} at {row['company']}{faang_badge}"):
            col1, col2, col3, col4 = st.columns(4)
            col1.write(f"**Location:** {row['location']}")
            col2.write(f"**Salary:** {row['salary_info']}")
            col3.write(f"**Category:** {row['fit_category']}")
            col4.write(f"**Date:** {str(row['posted_date'])[:10]}")
            
            st.info(f"**🤖 AI Evaluation:** {row['justification']}")
            
            if row['url']:
                st.markdown(f"[**Apply Here**]({row['url']})")

if __name__ == "__main__":
    main()
