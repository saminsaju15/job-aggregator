# AI-Powered Job Aggregator Dashboard

An automated job aggregation and filtering system using Python, Streamlit, RapidAPI (JSearch), and Gemini AI. This repository is configured to run automatically in the cloud every day, finding and evaluating jobs against a Senior Business Process Analyst persona.

## How it Works

1. **Daily Automation**: A GitHub Actions workflow (`.github/workflows/scraper.yml`) runs the `main_scraper.py` script automatically every day at 7:00 PM EST.
2. **AI Evaluation**: The scraper fetches jobs matching specific keywords and locations via RapidAPI, and then uses the Gemini API to evaluate them.
3. **Database Updates**: Jobs categorized as a "Strong Fit" or "Reach" are saved to `job_tracker.db`. The GitHub Action automatically commits this updated database back to the repository.
4. **Live Dashboard**: A Streamlit Community Cloud application reads from this updated database and displays the curated jobs on a public URL.

## Setup & Deployment Guide

This project is designed to be hosted entirely online. Follow these steps to set it up:

### Step 1: Upload to GitHub
1. Go to [GitHub](https://github.com/) and create a new public repository (e.g., `job-aggregator`). Do not initialize it with a README.
2. Once created, click on the **"uploading an existing file"** link on the quick setup page.
3. Open your local `Job Aggregator` folder on your computer.
4. Drag and drop **all files and folders** (including the `.github` folder, `app.py`, `main_scraper.py`, `requirements.txt`, and `job_tracker.db`) into the GitHub window.
5. Click **"Commit changes"**.

### Step 2: Add API Keys to GitHub (For the Scraper)
*The GitHub Action needs your API keys to run the scraper, but they must be kept secret.*
1. On your GitHub repository page, click the **Settings** tab at the top.
2. In the left sidebar, scroll down to **Secrets and variables** and click **Actions**.
3. Click the green **"New repository secret"** button.
4. **First Secret**:
   - Name: `RAPIDAPI_KEY`
   - Secret: *(Paste your RapidAPI key here)*
   - Click **Add secret**.
5. **Second Secret**:
   - Name: `GEMINI_API_KEY`
   - Secret: *(Paste your Gemini API key here)*
   - Click **Add secret**.

### Step 3: Deploy the Streamlit App
1. Go to [Streamlit Community Cloud](https://share.streamlit.io/) and log in with your GitHub account.
2. Click **"New app"** (or "Create app").
3. Select the repository you just created (e.g., `yourusername/job-aggregator`).
4. Set the **Branch** to `main`.
5. Set the **Main file path** to `app.py`.
6. **Important**: Before clicking Deploy, click on **"Advanced settings..."** (or "Secrets").
7. In the Secrets text box, enter your API keys like this:
   ```toml
   RAPIDAPI_KEY = "your_rapid_api_key_here"
   GEMINI_API_KEY = "your_gemini_api_key_here"
   ```
8. Click **Save**, and then click **Deploy!**

Your app will take a minute or two to build, and then you will have a live, public URL containing your dashboard. The GitHub Action will automatically run every evening at 7:00 PM EST, updating the database, which will immediately reflect on your live dashboard.
