"""Periodic job runner for the MarketSentiment data pipeline.

Runs the scrape -> analyze pipeline and the VIX alert monitor on fixed
intervals. Intervals are configurable through environment variables so the
same code works locally and inside the Docker scheduler container.
"""

import logging
import os
import subprocess
import sys
import time

import schedule
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXECUTABLE = sys.executable

WEBSCRAPE_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "website", "crucialPys", "webScrape.py")
ANALYZE_NEWS_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "website", "crucialPys", "analyze_news.py")
ALERT_MONITOR_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "website", "crucialPys", "alert_monitor.py")

PIPELINE_INTERVAL_MINUTES = int(os.environ.get("PIPELINE_INTERVAL_MINUTES", "25"))
ALERT_INTERVAL_MINUTES = int(os.environ.get("ALERT_INTERVAL_MINUTES", "5"))
SCRIPT_TIMEOUT_SECONDS = int(os.environ.get("SCRIPT_TIMEOUT_SECONDS", "900"))

LOG_DIR = os.path.join(PROJECT_ROOT, "scheduler_logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "scheduler.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("scheduler")


def run_script(script_path):
    script_basename = os.path.basename(script_path)

    if not os.path.exists(script_path):
        logger.error("Script not found: %s", script_path)
        return False

    logger.info("Starting %s", script_basename)
    try:
        result = subprocess.run(
            [PYTHON_EXECUTABLE, script_path],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            encoding="utf-8",
            errors="replace",
            timeout=SCRIPT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        logger.error("%s timed out after %s seconds", script_basename, SCRIPT_TIMEOUT_SECONDS)
        return False
    except Exception:
        logger.exception("Unexpected error while running %s", script_basename)
        return False

    if result.returncode != 0:
        logger.error(
            "%s failed (exit code %s)\nstdout:\n%s\nstderr:\n%s",
            script_basename,
            result.returncode,
            result.stdout or "N/A",
            result.stderr or "N/A",
        )
        return False

    logger.info("%s finished successfully", script_basename)
    if result.stdout:
        logger.debug("%s output:\n%s", script_basename, result.stdout)
    return True


def job_run_webscrape():
    return run_script(WEBSCRAPE_SCRIPT_PATH)


def job_run_analyze_news():
    return run_script(ANALYZE_NEWS_SCRIPT_PATH)


def job_run_alert_monitor():
    return run_script(ALERT_MONITOR_SCRIPT_PATH)


def combined_pipeline_job():
    if job_run_webscrape():
        job_run_analyze_news()
    else:
        logger.warning("Web scrape failed; skipping news analysis for this run.")


def main():
    logger.info(
        "Scheduler starting (pipeline every %s min, alerts every %s min)",
        PIPELINE_INTERVAL_MINUTES,
        ALERT_INTERVAL_MINUTES,
    )

    schedule.every(PIPELINE_INTERVAL_MINUTES).minutes.do(combined_pipeline_job)
    schedule.every(ALERT_INTERVAL_MINUTES).minutes.do(job_run_alert_monitor)

    # Run both jobs once at startup so the dashboard has fresh data
    # immediately after deployment instead of waiting a full interval.
    combined_pipeline_job()
    job_run_alert_monitor()

    while True:
        try:
            schedule.run_pending()
        except Exception:
            logger.exception("Scheduled job raised an unexpected error")
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user.")
