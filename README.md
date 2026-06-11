# Market Sentiment Dashboard

<div align="center">

![CI](https://github.com/dbogdanm/MarketSentiment/actions/workflows/ci.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
![Last Commit](https://img.shields.io/github/last-commit/dbogdanm/MarketSentiment?style=flat-square)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/postgresql-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/tailwindcss-%2338B2AC.svg?style=for-the-badge&logo=tailwind-css&logoColor=white)

</div>

A self-hosted dashboard that gauges stock-market mood. It aggregates financial news from public RSS feeds and Yahoo Finance (no API keys required), asks an LLM — a local Ollama model or a cloud provider — to summarize sentiment and produce a custom **Fear & Greed Index** (0–100), tracks the **VIX** with a multi-source fallback chain, stores history in PostgreSQL, and sends **email alerts** when the VIX crosses a subscriber's threshold.

## Features

- **News aggregation** from 10 RSS feeds (Google News, Yahoo Finance, Investing.com, MarketWatch, CNBC, …) plus Yahoo Finance ticker news — deduplicated, cleaned, capped at 300 articles per run.
- **AI sentiment analysis** via a configurable provider:
  - *Local:* Ollama (default, e.g. `deepseek-r1:1.5b`)
  - *Cloud:* Azure AI Inference or any OpenAI-compatible endpoint
  - Providers and keys are managed at runtime from the in-app **/settings** page.
- **VIX retrieval with fallbacks:** yfinance history → yfinance fast_info → CNBC quote API → Stooq.
- **Interactive dashboard:** Fear & Greed gauge, VIX card, historical charts (Chart.js), date-range filtering, recent-history table, dark/light mode, Markdown-rendered AI summary, CSV and PDF export.
- **VIX email alerts:** per-user thresholds, HTML emails over SMTP, 6-hour cooldown per subscriber (configurable).
- **Automation:** a scheduler container runs the scrape → analyze pipeline every 25 minutes and the alert check every 5 minutes (both configurable); the dashboard also has manual *Scraper / Analyzer / Refresh All* buttons.
- **Operations-ready:** `/healthz` endpoint, container healthchecks, structured logging in every component, non-root Docker image, CI with lint + tests + Docker build.

## Architecture

```
                ┌─────────────────────────── scheduler container ───────────────────────────┐
                │  scheduler_main.py                                                         │
                │   ├─ every 25 min: webScrape.py ──► financial_news_agg.json               │
                │   │                 analyze_news.py ──► PostgreSQL + latest_indices.json  │
                │   └─ every 5 min:  alert_monitor.py ──► SMTP email alerts                 │
                └────────────────────────────────────────────────────────────────────────────┘
                                  │                                   │
                                  ▼                                   ▼
                          ┌──────────────┐                   ┌──────────────────┐
                          │  PostgreSQL  │ ◄──────────────── │  web container   │
                          │  (db)        │                   │  Flask + gunicorn│──► Dashboard :5000
                          └──────────────┘                   └──────────────────┘
```

| Component | File | Role |
| :-- | :-- | :-- |
| Data ingestion | `website/crucialPys/webScrape.py` | Fetch news + VIX, write JSON aggregate |
| AI analysis | `website/crucialPys/analyze_news.py` | LLM call, parse F&G score, persist results |
| Alerting | `website/crucialPys/alert_monitor.py` | Compare VIX to subscriptions, send emails |
| Web app | `website/appFlask.py` | Dashboard, settings, CSV export, healthcheck, manual pipeline triggers |
| Scheduler | `scheduler_main.py` | Periodic orchestration of the three scripts |
| DB schema | `db/init.sql` | Tables `sentiment_history`, `vix_alerts_subscriptions` (auto-applied) |

## Quick Start (Docker — recommended)

Requirements: Docker with the Compose plugin.

```bash
git clone https://github.com/dbogdanm/MarketSentiment
cd MarketSentiment

# 1. Configure secrets
cp .env.example .env
#    Edit .env — FLASK_SECRET_KEY is required; generate one with:
#    python -c "import secrets; print(secrets.token_hex(32))"

# 2. Launch (db + web + scheduler)
docker compose up -d --build
```

The dashboard is now at **http://localhost:5000**. The database schema is created automatically on first boot, and the scheduler immediately runs a first scrape so the dashboard has data within a minute or two.

> **Note:** the AI summary needs a model. Either run [Ollama](https://ollama.com) on the host (default endpoint `http://localhost:11434`) or open **Settings** in the app and point it at a cloud provider. Without a model, the pipeline still collects news and VIX data gracefully.

## Manual Setup (without Docker)

```bash
# 1. Python environment
python -m venv .venv
# Windows: .\.venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 2. Build the Tailwind stylesheet
npm install
npm run build:css

# 3. Configuration
cp .env.example .env        # set DB credentials, FLASK_SECRET_KEY, SMTP, ...
                            # DB_HOST=localhost for a local PostgreSQL

# 4. Database — start PostgreSQL and create the database; the schema is
#    created automatically when the web app starts (or run db/init.sql once).

# 5. Run
python website/appFlask.py   # dashboard at http://127.0.0.1:5000
python scheduler_main.py     # pipeline + alerts (separate terminal)
```

## Configuration

All settings come from environment variables (`.env`, loaded automatically — see `.env.example`):

| Variable | Default | Purpose |
| :-- | :-- | :-- |
| `FLASK_SECRET_KEY` | — (**required in production**) | Session/CSRF signing key |
| `DB_HOST` / `DB_NAME` / `DB_USER` / `DB_PASS` | `db` / `marketsentiment` / `user` / `password` | PostgreSQL connection |
| `PIPELINE_INTERVAL_MINUTES` | `25` | Scrape + analyze frequency |
| `ALERT_INTERVAL_MINUTES` | `5` | VIX alert check frequency |
| `ALERT_COOLDOWN_HOURS` | `6` | Minimum gap between emails per subscriber |
| `SMTP_SERVER` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` | empty (alerts disabled) | Outgoing email |
| `GUNICORN_WORKERS` / `GUNICORN_TIMEOUT` | `2` / `120` | Web server tuning |
| `LOG_LEVEL` | `INFO` | Logging verbosity for all components |
| `AUTO_INIT_DB` | `1` | Set `0` to skip schema init at startup |

AI provider settings (Ollama endpoint/model, cloud endpoint/key/model) live in `website/data_files/ai_config.json` and are edited from the **/settings** page; the API key is write-only in the UI and never rendered back.

## HTTP Endpoints

| Route | Method | Description |
| :-- | :-- | :-- |
| `/` | GET/POST | Dashboard; POST subscribes/updates a VIX alert |
| `/settings` | GET/POST | AI provider configuration |
| `/export/csv` | GET | Download history (honors date filters) |
| `/healthz` | GET | Liveness + DB status (used by container healthcheck) |
| `/run_webscrape`, `/run_analyze_news`, `/run_pipeline` | POST | Manual pipeline triggers (serialized; concurrent calls get `409`) |

> The manual trigger and settings endpoints are unauthenticated by design (single-user tool). If you expose the app publicly, put it behind a reverse proxy with authentication.

## Development

```bash
pip install -r requirements-dev.txt

pytest                                          # test suite
ruff check website tests scheduler_main.py     # lint
```

CI (`.github/workflows/ci.yml`) runs ruff + pytest on Python 3.11 and 3.13, builds the Docker image, and validates the compose file on every push and pull request.

### Project Layout

```
├── website/
│   ├── appFlask.py          # Flask app
│   ├── crucialPys/          # webScrape / analyze_news / alert_monitor
│   ├── templates/           # Jinja2 (Tailwind CSS)
│   ├── static/              # JS, images, built style.css (generated)
│   └── data_files/          # runtime JSON cache + AI config (gitignored)
├── scheduler_main.py        # periodic job runner
├── db/init.sql              # database schema
├── tests/                   # pytest suite
├── Dockerfile               # multi-stage: Node (Tailwind) → Python
└── docker-compose.yml       # db + web + scheduler
```

## License

MIT — Copyright (c) 2026 **Dinu Bogdan**. See [LICENSE](LICENSE).

## Contact

Maintainer: **Dinu Bogdan-Marius** · `bogdandinu625@gmail.com` · GitHub [@dbogdanm](https://github.com/dbogdanm)

For issues or feature requests, please open a GitHub issue.
