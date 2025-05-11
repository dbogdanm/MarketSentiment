# Market Sentiment Dashboard & AI Analyzer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Uncover market sentiment by leveraging AI-driven insights from aggregated financial news.** This sophisticated web application provides a dynamic dashboard displaying key indicators like a custom Fear & Greed Index, the VIX, and historical trends, all powered by real-time data, intelligent analysis, and **proactive VIX alert notifications**.

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
    *   [VIX Alert Monitor](#vix-alert-monitor)
*   [Key Configuration Points](#key-configuration-points)
*   [Roadmap & Potential Enhancements](#roadmap--potential-enhancements)
*   [Contribution Guidelines](#contribution-guidelines)
*   [License](#license)
*   [Contact & Support](#contact--support)

---

## Introduction

The Market Sentiment Dashboard is designed to offer a consolidated and intelligent view of the prevailing mood in the financial markets. It achieves this by:

1.  **Aggregating:** Systematically collecting news articles from a diverse range of reputable financial sources.
2.  **Analyzing:** Employing an advanced AI model (Azure DeepSeek deployed via Azure AI Services) to process the aggregated news, generating a unique Fear & Greed Index and a concise sentiment summary.
3.  **Integrating:** Fetching the latest VIX (Volatility Index) data to complement the sentiment analysis.
4.  **Persisting:** Storing historical sentiment data (Fear & Greed Index, VIX, AI summary, timestamps) within a robust PostgreSQL database for trend analysis.
5.  **Visualizing:** Presenting these insights through an intuitive Flask-powered web dashboard, featuring an F&G gauge, VIX display, interactive historical charts, and a recent activity table.
6.  **Notifying:** Proactively alerting subscribed users via email when the VIX crosses their predefined thresholds, keeping them informed of significant market volatility changes.

This tool empowers users to quickly gauge market undercurrents, supported by data-driven AI and timely alerts.

---

## Core Features

*   **Comprehensive News Aggregation:** Gathers financial news from premier RSS feeds (e.g., Yahoo Finance, Investing.com) and the NewsAPI (sourcing from outlets like Bloomberg, Reuters, The Wall Street Journal).
*   **AI-Driven Sentiment Intelligence:** Utilizes Azure AI Services (specifically a deployed DeepSeek model) to:
    *   Distill a succinct **market sentiment summary** from complex news data.
    *   Calculate a proprietary **Fear & Greed Index** (scaled 1-100).
*   **Real-time VIX Monitoring:** Retrieves the most current VIX index values via `yfinance`.
*   **Persistent Historical Data:** Archives all analysis results, enabling insightful trend observation and historical review.
*   **Dynamic & Interactive Dashboard:** Offers a rich user experience with:
    *   A clear visual **gauge** for the current Fear & Greed Index.
    *   **Line charts** illustrating historical Fear & Greed and VIX trajectories.
    *   A sortable **table** detailing recent analysis records.
    *   **PDF Export:** Allows users to download a snapshot of the current dashboard view.
    *   **Enhanced User Control:** Includes 'Run Scraper', 'Run Analyzer', and 'Refresh All Data' buttons directly within the interface for simplified manual operation and data management.
*   **Proactive VIX Email Alerts:**
    *   Users can subscribe to receive email notifications when the VIX surpasses a custom-defined threshold.
    *   Alerts include current VIX value, user's threshold, and a timestamp.
    *   Configurable minimum interval between alerts to prevent spam.
*   **Modern Web Interface:** Developed with Flask, HTML5, CSS3, and JavaScript, incorporating Gauge.js and Chart.js for superior data visualization.
*   **Automated Data Refresh & Alert Monitoring:** Includes a Python-based scheduler (`scheduler_main.py`) to automate the data collection, analysis pipeline, and VIX alert checks at configurable intervals.

---

## System Architecture

The application employs a layered architecture for modularity and maintainability:

*   **Data Ingestion Layer (`webScrape.py`):** Responsible for fetching raw news data and VIX values from external sources.
*   **AI Analysis & Processing Layer (`analyze_news.py`):** Handles communication with the Azure AI service, parses AI responses, and prepares data for storage.
*   **Notification Layer (`alert_monitor.py`):** Monitors VIX values, checks user subscriptions, and dispatches email alerts via SMTP.
*   **Persistence Layer:**
    *   **PostgreSQL Database:**
        *   `sentiment_history`: Stores historical sentiment records.
        *   `vix_alerts_subscriptions`: Manages user subscriptions for VIX alerts (email, threshold, last alert timestamp).
    *   **JSON Files:** Used for intermediate data storage (`financial_news_agg.json`) and caching the latest index values (`latest_indices.json`) for rapid dashboard loading.
*   **Presentation Layer (`appFlask.py` & Frontend):** The Flask application serves the web dashboard, retrieving data from the database, managing VIX alert subscriptions, and presenting it through HTML templates enhanced with CSS and JavaScript.
*   **Scheduling Layer (`scheduler_main.py`):** Orchestrates the periodic execution of the data ingestion, analysis, and VIX alert monitoring scripts.

---

## Technology Ecosystem

*   **Backend Framework:** Python 3.x, Flask
*   **Frontend Technologies:** HTML5, CSS3, JavaScript (ES6+)
*   **Frontend Visualization Libraries:** Gauge.js, Chart.js, html2canvas, jsPDF
*   **Data Acquisition & Parsing:** `feedparser`, `newsapi-python`, `yfinance`, `requests`, `beautifulsoup4`
*   **Artificial Intelligence:** Azure AI Services (via `azure-ai-inference` SDK for custom deployed models like DeepSeek)
*   **Database System:** PostgreSQL
*   **Database Connector (Python):** `psycopg2-binary`
*   **Email Notifications:** `smtplib` (Python's built-in SMTP library)
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
*   SMTP server credentials for sending email alerts (e.g., Gmail App Password if using Gmail with 2FA).

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/your-repository-name.git # Replace with your actual repository URL
    cd your-repository-name # Navigate to the project root directory
    ```

2.  **Create and Activate a Python Virtual Environment:**
    A common name for the virtual environment directory is `.venv`. If you use a different name, please adjust the activation paths accordingly.
    ```bash
    # Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # macOS / Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies:**
    Ensure you have a `requirements.txt` file in the project root.
    ```bash
    pip install -r requirements.txt
    ```

### Database Configuration

1.  **Connect to your PostgreSQL instance.**
2.  **Create a new database** (e.g., `market_sentiment_db`).
3.  **Create a dedicated user** and grant it necessary privileges on the new database.
4.  **Execute the Data Definition Language (DDL) scripts to create the necessary tables:**

    *   **For Sentiment History:**
        ```sql
        CREATE TABLE sentiment_history (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            fear_greed INTEGER,
            vix REAL, -- Or NUMERIC(5, 2) for fixed precision if preferred
            summary_text TEXT
        );
        -- Optional: Create an index for faster querying on the timestamp column
        CREATE INDEX idx_sentiment_history_timestamp ON sentiment_history (timestamp DESC);
        ```

    *   **For VIX Alert Subscriptions:**
        ```sql
        CREATE TABLE vix_alerts_subscriptions (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            vix_threshold REAL NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            subscribed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            last_alert_sent_at TIMESTAMPTZ,
            unsubscribe_token VARCHAR(64) UNIQUE -- Optional: for one-click unsubscribe links
        );
        -- Optional: Index for active subscriptions
        CREATE INDEX idx_vix_alerts_active_threshold ON vix_alerts_subscriptions (is_active, vix_threshold);
        ```

### Environment Configuration

1.  **Create an Environment File:** In the project root directory (e.g., `ProiectMarketSentimentMDS`), create a file named `.env`.
2.  **Populate `.env` with your credentials and configuration:**
    ```dotenv
    # .env example
    NEWSAPI_KEY="YOUR_ACTUAL_NEWSAPI_KEY"
    AZURE_DEEPSEEK_API_KEY="YOUR_ACTUAL_AZURE_AI_KEY"
    AZURE_ENDPOINT_URL="YOUR_AZURE_MODEL_ENDPOINT_URL" # e.g., https://your-resource.inference.ai.azure.com
    MODEL_NAME="YOUR_AZURE_MODEL_DEPLOYMENT_NAME" # e.g., deepseek-coder-6.7b-instruct

    DB_NAME="market_sentiment_db"
    DB_USER="your_db_user"
    DB_PASS="your_db_password"
    DB_HOST="localhost" # Or your PostgreSQL server address
    DB_PORT="5432" # Optional, defaults to 5432 if not specified

    # SMTP Configuration for Email Alerts
    SMTP_SERVER="smtp.example.com" # e.g., smtp.gmail.com
    SMTP_PORT="587" # Or 465 for SSL
    SMTP_USER="your_email_address@example.com" # Email address to send alerts from
    SMTP_PASS="your_email_password_or_app_password" # For Gmail with 2FA, use an App Password
    ```
3.  **Security:** Add `.env` to your `.gitignore` file to prevent accidental commitment of sensitive credentials.

---

## Running the Application

The application consists of a data pipeline (scraping and analysis), an alert monitor, and a web dashboard.

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
    *Note: These scripts can also be triggered from the web interface after launching the dashboard.*

*   **Automated Execution (Recommended):**
    See [Automated Scheduling](#automated-scheduling-recommended) below.

### Launching the Web Dashboard

1.  Ensure your virtual environment is activated.
2.  Navigate to the project root directory.
3.  Start the Flask development server:
    ```bash
    python website/appFlask.py
    ```
    *(If `appFlask.py` is in the root, use `python appFlask.py`)*
4.  Open your web browser and navigate to `http://127.0.0.1:5000` (or the URL displayed in the terminal).
    The dashboard will allow users to subscribe/unsubscribe to VIX alerts.

### Automated Scheduling (Recommended)

For continuous, unattended operation (while your machine is running), use the `scheduler_main.py` script. This script handles the periodic execution of the data pipeline and the VIX alert monitor.

1.  Ensure your virtual environment is activated.
2.  Navigate to the project root directory.
3.  Run the Python-based scheduler:
    ```bash
    python scheduler_main.py
    ```
This script will run continuously in the terminal, executing `webScrape.py`, `analyze_news.py`, and `alert_monitor.py` sequentially at configurable intervals (default is 30 minutes for data pipeline, and a separate interval for alert monitor - typically more frequent, e.g., every 5-15 minutes, if configured). Log files will be generated in the `scheduler_logs` directory. Press `Ctrl+C` to stop the scheduler.

The default 30-minute interval for the news scheduler is designed to be well within the free tier limits of NewsAPI (100 calls/day), resulting in approximately 48 calls daily. The VIX alert monitor's frequency should be set considering `yfinance`'s rate limits and the desired responsiveness of alerts.

### VIX Alert Monitor

The `alert_monitor.py` script is responsible for checking the current VIX value against subscribed user thresholds and sending email alerts.

*   **Manual Execution (for testing):**
    ```bash
    python website/crucialPys/alert_monitor.py
    ```
*   **Automated Execution:** This script is typically run by `scheduler_main.py`.

---

## Key Configuration Points

Fine-tune the application's behavior by adjusting parameters:

*   **API Keys, Database Credentials, AI Endpoints, SMTP Settings (`.env` file):** This is the primary location for all sensitive and environment-specific configurations.
*   **News Sources (`webScrape.py`):** Modify `NEWSAPI_SOURCES` and `ALL_RSS_FEEDS` lists within the script if necessary.
*   **Financial Tickers (`webScrape.py`):** Adjust the `YAHOO_TICKERS` list.
*   **AI Model Configuration (`analyze_news.py` & `.env`):** The `AZURE_ENDPOINT_URL` and `MODEL_NAME` (your Azure deployment name) are primarily loaded from the `.env` file.
*   **File Paths & Output (`webScrape.py`, `analyze_news.py`):** Constants like `OUTPUT_DIR`, `JSON_NEWS_FILE_PATH` are defined at the top of these scripts.
*   **Scheduling Intervals (`scheduler_main.py`):** Modify the `schedule.every(...).minutes.do(...)` lines for `webScrape.py`, `analyze_news.py`, and `alert_monitor.py` to change their execution frequencies.
*   **Alerting Parameters (`alert_monitor.py`):**
    *   `MIN_ALERT_INTERVAL`: Defines the minimum time (e.g., 6 hours) between consecutive alerts to the same user to prevent spamming.
    *   Email templates and content can be modified within this script.

---

## Roadmap & Potential Enhancements

This project serves as a strong foundation. Future enhancements could include:

*   **Advanced Error Handling & Logging:** Implement comprehensive logging using Python's `logging` module across all scripts for better diagnostics.
*   **More Frequent VIX Updates:** Investigate robust methods (e.g., Selenium, Playwright, or specialized APIs) for more frequent VIX updates, while being mindful of source limitations and script fragility.
*   **Enhanced Data Visualization:** Introduce date range selectors for charts, more detailed tooltips, and potentially new chart types (e.g., heatmaps for sector sentiment).
*   **User Authentication & Personalization:** Allow users to create accounts, save preferences, or track specific assets beyond just VIX alerts.
*   **Nuanced Sentiment Scoring:** Explore advanced NLP models or techniques for multi-dimensional sentiment analysis (e.g., positivity, negativity, uncertainty, specific emotions).
*   **Asynchronous Data Fetching:** Utilize `asyncio` and `aiohttp` in `webScrape.py` to potentially accelerate news aggregation from multiple sources concurrently.
*   **Containerization (Docker):** Package the application and its dependencies into Docker containers for simplified deployment, scalability, and portability.
*   **Enhanced Alerting System:**
    *   Allow users to manage their alert subscriptions (threshold, active status) directly from the dashboard.
    *   Implement one-click unsubscribe links in alert emails.
    *   Add alerts for critical data pipeline failures.
*   **Dashboard UI for Alert Management:** Integrate forms and views in `appFlask.py` for users to subscribe, update, or unsubscribe from VIX alerts.

---

## Contribution Guidelines

We welcome contributions! If you'd like to contribute, please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix (e.g., `git checkout -b feature/your-feature-name` or `fix/your-bug-fix`).
3.  Make your changes and commit them with clear, descriptive messages.
4.  Push your changes to your forked repository.
5.  Submit a Pull Request to the main repository, detailing the changes you've made and their purpose.

---

## License

This project is proudly licensed under the MIT License. See the `LICENSE.md` file for full details.

---

## Contact & Support

Project Maintainer: Dinu Bogdan-Marius
Email: `bogdandinu625@gmail.com`
GitHub: `dbogdanm`

For issues, feature requests, or support, please open an issue on the GitHub repository.