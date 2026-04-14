# Market Sentiment Dashboard & AI Analyzer

<div align="center">

![Status](https://img.shields.io/badge/Maintained-yes-brightgreen.svg?style=flat-square)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
![Repo Size](https://img.shields.io/github/repo-size/dbogdanm/MarketSentiment?style=flat-square)
![Last Commit](https://img.shields.io/github/last-commit/dbogdanm/MarketSentiment?style=flat-square)

<br/>

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/numpy-%23013243.svg?style=for-the-badge&logo=numpy&logoColor=white)
![Stock Market](https://img.shields.io/badge/Market-Analysis-green?style=for-the-badge&logo=google-finance&logoColor=white)
![AI](https://img.shields.io/badge/AI-Sentiment-blueviolet?style=for-the-badge)

</div>

**Uncover market sentiment by leveraging AI-driven insights from aggregated financial news.** This sophisticated web application provides a dynamic dashboard displaying key indicators like a custom Fear & Greed Index, the VIX, and historical trends, all powered by real-time data, intelligent analysis, and **proactive VIX alert notifications**.

---
-----

## What's New: Version 1.0 vs. Version 2.0 (Latest Update)

The architecture and user experience have been completely overhauled for stability, aesthetic appeal, and deployment ease.

| Feature Area | Version 1.0 (Old) | Version 2.0 (New) |
| :--- | :--- | :--- |
| **VIX Data Retrieval** | Single point of failure (`yfinance`). Prone to silent failures during off-hours or API blocks. | **Multi-Source Fallback System:** `yfinance` -\> CNBC API -\> Stooq. Uses 5-day lookbacks and standard User-Agents to prevent 403 errors. |
| **AI Output Formatting** | Raw, unformatted text blocks containing redundant system prompt data. | **Rich Markdown Rendering:** Uses `marked.js` for beautiful lists and bold text. Regex automatically strips redundant technical lines from the UI. |
| **Alert System** | Susceptible to broken imports; disconnected from real-time syncs. | **Fully Functional & Synced:** Fixed core import errors. Data flow seamlessly syncs between the scraper, JSON cache, and PostgreSQL. |
| **User Interface** | Basic static theme; visual components required manual refreshes to sync. | **Modern & Persistent UI:** Dark/Light mode toggle with `localStorage` persistence. Gauges and charts dynamically update colors on theme switch. |
| **Deployment** | Manual script execution in virtual environments. | **Enterprise Docker Architecture:** Single `docker-compose up` command orchestrates DB, Web (Gunicorn), and Scheduler containers. |

-----

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

Follow these steps to get the Market Sentiment Dashboard running.

### Deploying with Docker (Recommended)

The easiest way to run the application is using Docker. This ensures all databases, web servers, and background schedulers boot up perfectly synced.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/dbogdanm/MarketSentiment
    cd MarketSentiment
    ```
2.  **Configure Environment Variables:**
    Copy the sample environment file and fill in your API keys and SMTP credentials.
    ```bash
    cp .env.example .env
    ```
3.  **Launch the Application:**
    ```bash
    docker-compose up -d
    ```
    *The dashboard is now live at `http://localhost:5000`.*

### Manual / Local Installation

If you prefer running without Docker:

1.  **Create and Activate a Python Virtual Environment:**
    ```bash
    python -m venv .venv
    # Windows: .\.venv\Scripts\activate
    # macOS/Linux: source .venv/bin/activate
    ```
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Database Configuration:**
    Ensure PostgreSQL is running locally, create a `market_sentiment_db` database, and execute the SQL table creations found in the `schema.sql` (or see the old instructions for table schema).
4.  **Set `.env` variables** (same as Docker setup).


## Running the Application

If you are running the app locally (without Docker Compose), you need to start the components manually:

**1. Launching the Web Dashboard:**

```bash
python website/appFlask.py
```

**2. Automated Scheduling (Data Pipeline & Alerts):**
For continuous operation of the fallback APIs, AI analysis, and alert system:

```bash
python scheduler_main.py
```

*(Note: If using Docker, `scheduler_main.py` is already running autonomously in its own container).*

-----

## Key Configuration Points

  * **API Keys & Credentials (`.env`):** Primary location for NewsAPI, Azure AI/Ollama endpoints, Postgres credentials, and SMTP settings.
  * **VIX Fallback Logic (`webScrape.py`):** The logic prioritizing `yfinance` -\> `CNBC` -\> `Stooq` can be adjusted here, along with the 5-day lookback window.
  * **AI Prompting (`analyze_news.py`):** Modify the system prompts to further tweak how the AI formats its Markdown response.
  * **Scheduling Intervals (`scheduler_main.py`):** Modify `schedule.every(...).minutes` to change scraping and alerting frequencies.

-----

## Roadmap & Potential Enhancements

  * **Advanced Error Handling:** Implement comprehensive Python `logging` for deeper diagnostics across the Docker containers.
  * **User Authentication:** Allow users to create accounts to save personal dashboard layouts and track specific assets beyond just VIX alerts.
  * **Enhanced UI Data Visualization:** Introduce date range selectors for historical charts and detailed sector-sentiment heatmaps.
  * **Asynchronous Data Fetching:** Utilize `asyncio` and `aiohttp` in `webScrape.py` to accelerate news aggregation.



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


---

## Contribution Guidelines

We welcome contributions! If you'd like to contribute, please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix (e.g., `git checkout -b feature/your-feature-name` or `fix/your-bug-fix`).
3.  Make your changes and commit them with clear, descriptive messages.
4.  Push your changes to your forked repository.
5.  Submit a Pull Request to the main repository, detailing the changes you've made and their purpose.

---

---

## License

**Copyright (c) 2026 DINU BOGDAN**

This project is licensed under the MIT License.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## Contact & Support

Project Maintainer: Dinu Bogdan-Marius
Email: `bogdandinu625@gmail.com`
GitHub: `dbogdanm`

For issues, feature requests, or support, please open an issue on the GitHub repository.
