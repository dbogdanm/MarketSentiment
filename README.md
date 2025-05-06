# Market Sentiment Dashboard

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A web application that aggregates financial news, analyzes market sentiment using AI, and displays key indicators like the Fear & Greed Index and VIX.


## Table of Contents

*   [Overview](#overview)
*   [Features](#features)
*   [Technology Stack](#technology-stack)
*   [Setup and Installation](#setup-and-installation)
*   [Usage](#usage)
*   [Project Structure](#project-structure)
*   [Configuration](#configuration)
*   [Future Improvements](#future-improvements)
*   [Contributing](#contributing)
*   [License](#license)
*   [Contact](#contact)

## Overview

This project aims to provide a quick overview of the current financial market sentiment by:

1.  **Scraping:** Aggregating news articles from various financial sources (RSS feeds, NewsAPI).
2.  **Analyzing:** Sending the aggregated news to an AI model (Azure DeepSeek via Azure AI Services) to estimate the Fear & Greed Index and summarize sentiment.
3.  **Fetching Data:** Retrieving the latest VIX index value using the `yfinance` library.
4.  **Storing:** Persisting historical sentiment analysis results (F&G, VIX, summary, timestamp) in a PostgreSQL database.
5.  **Displaying:** Presenting the latest F&G index via a gauge, the current VIX value, historical trends via charts, and recent history in a table using a Flask web application.

## Features

*   **Multi-Source News Aggregation:** Fetches news from RSS (Google News, Yahoo Finance, Investing.com, etc.) and NewsAPI (Bloomberg, Reuters, WSJ, etc.).
*   **AI-Powered Sentiment Analysis:** Leverages Azure AI Services (DeepSeek model) to generate:
    *   A concise summary of market sentiment based on news headlines.
    *   An estimated Fear & Greed Index (1-100).
*   **Real-time VIX Fetching:** Retrieves the latest available VIX index value using `yfinance`.
*   **Historical Data Tracking:** Stores analysis results over time in a PostgreSQL database.
*   **Interactive Dashboard:** Displays key metrics using:
    *   A visual gauge for the Fear & Greed Index.
    *   Line charts for historical F&G and VIX trends.
    *   A table showing recent analysis records.
*   **Web Interface:** Built with Flask, HTML, CSS, and JavaScript (Gauge.js, Chart.js).

## Technology Stack

*   **Backend:** Python 3.x, Flask
*   **Frontend:** HTML5, CSS3, JavaScript (ES6+)
*   **Frontend Libraries:** Gauge.js, Chart.js
*   **Data Scraping:** `feedparser`, `newsapi-python`, `yfinance`, `requests`, `beautifulsoup4`
*   **AI Service:** Azure AI Services (using `azure-ai-inference` SDK for a deployed model like DeepSeek)
*   **Database:** PostgreSQL
*   **Database Connector:** `psycopg2-binary`
*   **Environment Variables:** `python-dotenv` (recommended)
*   **Version Control:** Git & GitHub

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/dbogdanm/Market.git
    cd MarketSentiment # Or your actual root project folder name
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    # Windows
    python -m venv .venv1 
    .\.venv1\Scripts\activate

    # macOS / Linux
    python3 -m venv .venv1
    source .venv1/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt 
    # OR if you don't have requirements.txt yet:
    # pip install --upgrade psycopg2-binary azure-ai-inference azure-core feedparser newsapi-python yfinance beautifulsoup4 requests flask python-dotenv Chart.js gauge.js # Note: Chart.js/Gauge.js are typically included via CDN in HTML
    ```
    *(Recommendation: Create a `requirements.txt` file using `pip freeze > requirements.txt` after installing)*

4.  **Set Up PostgreSQL Database:**
    *   Install PostgreSQL if you haven't already.
    *   Create a database (e.g., `market_sentiment_db`).
    *   Create a user and grant privileges to the database.
    *   Create the `sentiment_history` table (see SQL schema below or adapt from your setup):
      ```sql
      CREATE TABLE sentiment_history (
          id SERIAL PRIMARY KEY,
          timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
          fear_greed INTEGER,
          vix REAL, -- Or NUMERIC(5, 2)
          summary_text TEXT
      );
      CREATE INDEX idx_sentiment_history_timestamp ON sentiment_history (timestamp DESC);
      ```

5.  **Configure Environment Variables:**
    *   Create a file named `.env` in the project root directory (`ProiectMarketSentimentMDS`).
    *   Add the following variables, replacing placeholders with your actual credentials:
      ```dotenv
      # .env file
      NEWSAPI_KEY=YOUR_NEWSAPI_API_KEY
      AZURE_DEEPSEEK_API_KEY=YOUR_AZURE_AI_SERVICE_API_KEY

      # Database Credentials
      DB_NAME=your_database_name 
      DB_USER=your_database_user
      DB_PASS=your_database_password
      DB_HOST=localhost # Or your DB host if different
      
      # Azure Endpoint/Deployment (if not hardcoded in analyze_news.py)
      # AZURE_ENDPOINT_URL=YOUR_AZURE_ENDPOINT_URL 
      # AZURE_DEPLOYMENT_NAME=YOUR_AZURE_DEPLOYMENT_NAME
      ```
    *   **IMPORTANT:** Ensure your `.gitignore` file includes `.env` to avoid committing secrets.

## Usage

The project consists of two main scripts and the Flask web application:

1.  **Run the Scraper (`webScrape.py`):**
    *   This script fetches news and the VIX value and saves them to `website/data_files/financial_news_agg.json`.
    *   Navigate to the project root in your activated terminal.
    *   Run: `python website/crucialPys/webScrape.py`

2.  **Run the Analyzer (`analyze_news.py`):**
    *   This script reads the aggregated data, calls the Azure AI model for F&G estimation and summary, and saves the results to the database and `website/data_files/latest_indices.json`.
    *   Navigate to the project root in your activated terminal.
    *   Run: `python website/crucialPys/analyze_news.py`
    *   *(Ensure Azure endpoint/deployment name are correct in the script or via env vars)*

3.  **Run the Flask Web App (`appFlask.py`):**
    *   This script serves the dashboard webpage, reading the latest data from the database.
    *   Navigate to the `website` directory in your activated terminal.
    *   Run: `python appFlask.py`
    *   Open your web browser and go to `http://127.0.0.1:5000` (or the address shown in the terminal).

**Scheduling (Optional):** For continuous operation, you would typically schedule `webScrape.py` and `analyze_news.py` to run periodically (e.g., every hour or few hours) using tools like `cron` (Linux/macOS) or Task Scheduler (Windows). The Flask app would run continuously using a production server like Gunicorn or Waitress.


## Configuration

*   **API Keys & DB Credentials:** Set via the `.env` file (recommended) or directly as system environment variables.
*   **News Sources:** Modify `NEWSAPI_SOURCES` and `ALL_RSS_FEEDS` lists in `webScrape.py`.
*   **Tickers:** Adjust the `YAHOO_TICKERS` list in `webScrape.py`.
*   **AI Model:** Update `AZURE_ENDPOINT_URL` and `MODEL_NAME` (deployment name) in `analyze_news.py`.
*   **File Paths:** `OUTPUT_DIR`, `OUTPUT_FILENAME`, etc., are defined near the top of the scripts.

## Future Improvements

*   **Error Handling:** Implement more robust error handling and logging (using Python's `logging` module).
*   **Intraday VIX:** Explore more advanced web scraping techniques (e.g., using Selenium or Playwright) to potentially get a real-time intraday VIX, acknowledging the increased fragility.
*   **Data Visualization:** Enhance historical charts (e.g., add date range selection, tooltips with exact values).
*   **User Accounts:** Add user authentication to save preferences or track portfolios.
*   **Sentiment Nuance:** Explore more sophisticated NLP models for nuanced sentiment scoring beyond a single index.
*   **Asynchronous Operations:** Use `asyncio` for scraping to potentially speed up data fetching.
*   **CI/CD Pipeline:** Set up GitHub Actions for automated testing and deployment.
*   **Dockerization:** Containerize the application for easier deployment.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an Issue for bugs, features, or improvements. 

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 


## Contact

Dinu Bogdan-Marius - [<bogdandinu625@gmail.com>] - 



