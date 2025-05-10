# Market Sentiment Dashboard & AI Analyzer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Uncover market sentiment by leveraging AI-driven insights from aggregated financial news.** This sophisticated web application provides a dynamic dashboard displaying key indicators like a custom Fear & Greed Index, the VIX, and historical trends, all powered by real-time data and intelligent analysis.

---

## Table of Contents

*   [Introduction](#introduction)
*   [Core Features](#core-features)
*   [System Architecture](#system-architecture)
*   [Technology Ecosystem](#technology-ecosystem)
*   [Getting Started: Setup & Deployment](#getting-started-setup--deployment)
    *   [Prerequisites](#prerequisites)
    *   [Installation](#installation)
    *   [Database Configuration](#database-configuration)
    *   [Environment Configuration](#environment-configuration)
*   [Running the Application](#running-the-application)
    *   [Data Pipeline Execution](#data-pipeline-execution)
    *   [Launching the Web Dashboard](#launching-the-web-dashboard)
    *   [Automated Scheduling (Recommended)](#automated-scheduling-recommended)
*   [Key Configuration Points](#key-configuration-points)
*   [Roadmap & Potential Enhancements](#roadmap--potential-enhancements)
*   [Contribution Guidelines](#contribution-guidelines)
*   [License](#license)
*   [Contact & Support](#contact--support)

---

## Introduction

The Market Sentiment Dashboard is designed to offer a consolidated and intelligent view of the prevailing mood in the financial markets. It achieves this by:

1.  **Aggregating:** Systematically collecting news articles from a diverse range of reputable financial sources.
2.  **Analyzing:** Employing an advanced AI model (Azure DeepSeek via Azure AI Services) to process the aggregated news, generating a unique Fear & Greed Index and a concise sentiment summary.
3.  **Integrating:** Fetching the latest VIX (Volatility Index) data to complement the sentiment analysis.
4.  **Persisting:** Storing historical sentiment data (F&G, VIX, AI summary, timestamps) within a robust PostgreSQL database for trend analysis.
5.  **Visualizing:** Presenting these insights through an intuitive Flask-powered web dashboard, featuring an F&G gauge, VIX display, interactive historical charts, and a recent activity table.

This tool empowers users to quickly gauge market undercurrents, backed by data and AI.

---

## Core Features

*   **Comprehensive News Aggregation:** Gathers financial news from premier RSS feeds (Yahoo Finance, Investing.com, etc.) and the NewsAPI (sourcing from outlets like Bloomberg, Reuters, The Wall Street Journal).
*   **AI-Driven Sentiment Intelligence:** Utilizes Azure AI Services (specifically a deployed DeepSeek model) to:
    *   Distill a succinct **market sentiment summary** from complex news data.
    *   Calculate a proprietary **Fear & Greed Index** (scaled 1-100).
*   **Real-time VIX Monitoring:** Retrieves the most current VIX index values via `yfinance`.
*   **Persistent Historical Data:** Archives all analysis results, enabling insightful trend observation and historical review.
*   **Dynamic & Interactive Dashboard:** Offers a rich user experience with:
    *   A clear visual **gauge** for the current Fear & Greed Index.
    *   **Line charts** illustrating historical F&G and VIX trajectories.
    *   A sortable **table** detailing recent analysis records.
    *   **PDF Export:** Allows users to download a snapshot of the current dashboard.
*   **Modern Web Interface:** Developed with Flask, HTML5, CSS3, and JavaScript, incorporating Gauge.js and Chart.js for superior data visualization.
*   **Automated Data Refresh:** Includes a Python-based scheduler (`scheduler_main.py`) to automate the data collection and analysis pipeline at configurable intervals.

---

## System Architecture

The application employs a layered architecture for modularity and maintainability:

*   **Data Ingestion Layer (`webScrape.py`):** Responsible for fetching raw news data and VIX values from external sources.
*   **AI Analysis & Processing Layer (`analyze_news.py`):** Handles communication with the Azure AI service, parses AI responses, and prepares data for storage.
*   **Persistence Layer:**
    *   **PostgreSQL Database:** Stores historical sentiment records.
    *   **JSON Files:** Used for intermediate data storage (`financial_news_agg.json`) and caching the latest index values (`latest_indices.json`) for quick dashboard loading.
*   **Presentation Layer (`appFlask.py` & Frontend):** The Flask application serves the web dashboard, retrieving data from the database and presenting it through HTML templates enhanced with CSS and JavaScript.
*   **Scheduling Layer (`scheduler_main.py`):** Orchestrates the periodic execution of the data ingestion and analysis scripts.

---

## Technology Ecosystem

*   **Backend Framework:** Python 3.x, Flask
*   **Frontend Technologies:** HTML5, CSS3, JavaScript (ES6+)
*   **Frontend Visualization Libraries:** Gauge.js, Chart.js, html2canvas, jsPDF
*   **Data Acquisition & Parsing:** `feedparser`, `newsapi-python`, `yfinance`, `requests`, `beautifulsoup4`
*   **Artificial Intelligence:** Azure AI Services (via `azure-ai-inference` SDK for custom deployed models like DeepSeek)
*   **Database System:** PostgreSQL
*   **Database Connector (Python):** `psycopg2-binary`
*   **Task Scheduling (Python):** `schedule`
*   **Environment Management:** `python-dotenv` (for managing API keys and secrets)
*   **Version Control System:** Git & GitHub

---

## Getting Started: Setup & Deployment

Follow these steps to get the Market Sentiment Dashboard running on your local machine.

### Prerequisites

*   Python 3.8+
*   PostgreSQL server installed and running.
*   Git installed.
*   API keys for NewsAPI and Azure AI Services.

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/your-repository-name.git # Replace with your repo URL
    cd your-repository-name # Navigate to the project root
    ```

2.  **Create and Activate a Python Virtual Environment:**
    ```bash
    # Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # macOS / Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```
    *(We use `.venv` as a common name, but your `.venv1` is also fine; adjust paths accordingly.)*

3.  **Install Dependencies:**
    Ensure you have a `requirements.txt` file. If not, create one from the installed packages in your development environment (`pip freeze > requirements.txt`).
    ```bash
    pip install -r requirements.txt
    ```

### Database Configuration

1.  **Connect to your PostgreSQL instance.**
2.  **Create a new database:** e.g., `market_sentiment_db`.
3.  **Create a dedicated user** and grant it necessary privileges on the new database.
4.  **Execute the DDL to create the `sentiment_history` table:**
    ```sql
    CREATE TABLE sentiment_history (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        fear_greed INTEGER,
        vix REAL, -- Or NUMERIC(5, 2) for fixed precision
        summary_text TEXT
    );
    -- Optional: Index for faster querying on timestamp
    CREATE INDEX idx_sentiment_history_timestamp ON sentiment_history (timestamp DESC);
    ```

### Environment Configuration

1.  **Create an Environment File:** In the project root directory (e.g., `ProiectMarketSentimentMDS`), create a file named `.env`.
2.  **Populate `.env` with your credentials:**
    ```dotenv
    # .env example
    NEWSAPI_KEY="YOUR_ACTUAL_NEWSAPI_KEY"
    AZURE_DEEPSEEK_API_KEY="YOUR_ACTUAL_AZURE_AI_KEY"

    DB_NAME="market_sentiment_db"
    DB_USER="your_db_user"
    DB_PASS="your_db_password"
    DB_HOST="localhost" # Or your PostgreSQL server address
    # DB_PORT="5432" # Optional, if not default

    # Ensure these match your Azure AI model deployment if not hardcoded
    # AZURE_ENDPOINT_URL="YOUR_AZURE_MODEL_ENDPOINT_URL"
    # MODEL_NAME="YOUR_AZURE_MODEL_DEPLOYMENT_NAME"
    ```
3.  **Security:** Add `.env` to your `.gitignore` file to prevent accidental commitment of sensitive credentials.

---

## Running the Application

The application involves a data pipeline (scraping and analysis) and a web dashboard.

### Data Pipeline Execution

The data pipeline can be run manually or automatically using the provided scheduler.

*   **Manual Execution (for testing or initial run):**
    1.  Ensure your virtual environment is activated.
    2.  Navigate to the project root directory.
    3.  Execute the scraper:
        ```bash
        python website/crucialPys/webScrape.py
        ```
    4.  Once completed, execute the analyzer:
        ```bash
        python website/crucialPys/analyze_news.py
        ```

*   **Automated Execution (Recommended):**
    1.  Ensure your virtual environment is activated.
    2.  Navigate to the project root directory.
    3.  Run the Python-based scheduler:
        ```bash
        python scheduler_main.py
        ```
    This script will run continuously in the terminal, executing `webScrape.py` and `analyze_news.py` sequentially at 30-minute intervals (configurable in `scheduler_main.py`). Log files will be generated in the `scheduler_logs` directory. Press `Ctrl+C` to stop the scheduler.

### Launching the Web Dashboard

1.  Ensure your virtual environment is activated.
2.  Navigate to the project root directory (or the `website` subdirectory, depending on how your `appFlask.py` is structured for imports, but running from root is generally safer if paths are relative).
3.  Start the Flask development server:
    ```bash
    python website/appFlask.py
    ```
    *(If `appFlask.py` is in the root, use `python appFlask.py`)*
4.  Open your web browser and navigate to `http://127.0.0.1:5000` (or the URL displayed in the terminal).

### Automated Scheduling (Recommended)

For continuous, unattended operation (while your PC is on), use the `scheduler_main.py` script as described above. This script handles the periodic execution of the data pipeline.
No worries regarding API limits, the most limited API(NewsAPI) still has 100 free calls/day, running that scheduler every 30 minutes means that you've made 48 API calls.
---

## Key Configuration Points

Fine-tune the application's behavior by adjusting parameters in the respective Python scripts:

*   **API Keys & Database Credentials:** Managed via the `.env` file.
*   **News Sources (`webScrape.py`):** Modify `NEWSAPI_SOURCES` and `ALL_RSS_FEEDS` lists.
*   **Financial Tickers (`webScrape.py`):** Adjust the `YAHOO_TICKERS` list.
*   **AI Model Configuration (`analyze_news.py`):** Update `AZURE_ENDPOINT_URL` and `MODEL_NAME` (your Azure deployment name), or ensure they are loaded from environment variables.
*   **File Paths & Output (`webScrape.py`, `analyze_news.py`):** Constants like `OUTPUT_DIR`, `JSON_NEWS_FILE_PATH` are defined at the top of these scripts.
*   **Scheduling Interval (`scheduler_main.py`):** Modify the `schedule.every(...).minutes.do(...)` line.

---

## Roadmap & Potential Enhancements

This project serves as a strong foundation. Future enhancements could include:

*   **Advanced Error Handling & Logging:** Implement comprehensive logging using Python's `logging` module across all scripts.
*   **Real-time Intraday VIX:** Investigate robust methods (e.g., Selenium, Playwright, or specialized APIs) for more frequent VIX updates, while being mindful of source limitations and script fragility.
*   **Enhanced Data Visualization:** Introduce date range selectors for charts, more detailed tooltips, and potentially new chart types.
*   **User Authentication & Personalization:** Allow users to create accounts, save preferences, or track specific assets.
*   **Nuanced Sentiment Scoring:** Explore advanced NLP models or techniques for multi-dimensional sentiment analysis (e.g., positivity, negativity, uncertainty, specific emotions).
*   **Asynchronous Data Fetching:** Utilize `asyncio` and `aiohttp` in `webScrape.py` to potentially accelerate news aggregation.
*   **Containerization (Docker):** Package the application and its dependencies into Docker containers for simplified deployment and portability.
*   **Alerting System:** Notify userspeasants (e.g., via email) of significant sentiment shifts or data pipeline failures.

---

## Contribution Guidelines

We welcome contributions! If you'd like to contribute, please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix (`git checkout -b feature/your-feature-name` or `fix/your-bug-fix`).
3.  Make your changes and commit them with clear, descriptive messages.
4.  Push your changes to your forked repository.
5.  Submit a Pull Request to the main repository, detailing the changes you've made.




## License

This project is proudly licensed under the MIT License. See the [LICENSE.md](LICENSE.md) file for full details.

---

## Contact & Support

Project Maintainer: Dinu Bogdan-Marius
Email: `bogdandinu625@gmail.com`
GitHub: `dbogdanm` 

For issues, feature requests, or support, please open an issue on the GitHub repository.