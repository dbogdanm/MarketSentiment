import schedule
import time
import subprocess
import os
from datetime import datetime

PROJECT_MARKET_SENTIMENT_ROOT = os.path.dirname(os.path.abspath(__file__))

DESKTOP_PATH = os.path.abspath(os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, "..", ".."))

PYTHON_PROJECT1_FOLDER_NAME = "PythonProject1"
VENV_FOLDER_NAME = ".venv1"
SCRIPTS_FOLDER_NAME = "Scripts"
PYTHON_EXE_NAME = "python.exe"

PYTHON_EXECUTABLE = os.path.join(
    DESKTOP_PATH,
    PYTHON_PROJECT1_FOLDER_NAME,
    VENV_FOLDER_NAME,
    SCRIPTS_FOLDER_NAME,
    PYTHON_EXE_NAME
)

WEBSCRAPE_SCRIPT_RELATIVE_PATH = os.path.join("website", "crucialPys", "webScrape.py")
ANALYZE_NEWS_SCRIPT_RELATIVE_PATH = os.path.join("website", "crucialPys", "analyze_news.py")

WEBSCRAPE_SCRIPT_PATH = os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, WEBSCRAPE_SCRIPT_RELATIVE_PATH)
ANALYZE_NEWS_SCRIPT_PATH = os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, ANALYZE_NEWS_SCRIPT_RELATIVE_PATH)

LOG_DIR = os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, "scheduler_logs")
os.makedirs(LOG_DIR, exist_ok=True)

def run_script(script_path, log_file_name):
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = os.path.join(LOG_DIR, log_file_name)
    script_basename = os.path.basename(script_path)

    print(f"[{current_time_str}] Starting script: {script_basename}")
    try:
        if not os.path.exists(PYTHON_EXECUTABLE):
            raise FileNotFoundError(f"Python executable not found at: {PYTHON_EXECUTABLE}")
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found at: {script_path}")

        result = subprocess.run(
            [PYTHON_EXECUTABLE, script_path],
            check=True,
            capture_output=True,
            text=True,
            cwd=PROJECT_MARKET_SENTIMENT_ROOT,
            encoding='utf-8', errors='replace'
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- Log at {current_time_str} for {script_basename} ---\n")
            f.write("Output:\n")
            f.write(result.stdout if result.stdout else "N/A (No stdout)\n")
            f.write("\n--- End Log ---\n\n")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Script {script_basename} finished successfully.")
        return True

    except subprocess.CalledProcessError as e:
        error_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- ERROR at {error_time_str} for {script_basename} ---\n")
            f.write(f"Return code: {e.returncode}\n")
            f.write("Stdout:\n")
            f.write(e.stdout if e.stdout else "N/A (No stdout)\n")
            f.write("\nStderr:\n")
            f.write(e.stderr if e.stderr else "N/A (No stderr)\n")
            f.write("\n--- End Error Log ---\n\n")
        print(f"[{error_time_str}] ERROR running script {script_basename}. See {log_file_name}.")
        return False
    except FileNotFoundError as e:
        error_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{error_time_str}] FATAL ERROR: {e}")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- FATAL ERROR at {error_time_str} for {script_basename} ---\n")
            f.write(f"{e}\n")
            f.write(f"Check PYTHON_EXECUTABLE and script_path paths.\n")
            f.write(f"PYTHON_EXECUTABLE: {PYTHON_EXECUTABLE}\n")
            f.write(f"Script Path: {script_path}\n")
            f.write("\n--- End Error Log ---\n\n")
        return False
    except Exception as e:
        error_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{error_time_str}] An unexpected error occurred while running {script_basename}: {e}")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- UNEXPECTED ERROR at {error_time_str} for {script_basename} ---\n")
            f.write(f"Error: {e}\n")
            f.write(f"Error Type: {type(e)}\n")
            f.write("\n--- End Error Log ---\n\n")
        return False

def job_run_webscrape():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Preparing to run webScrape.py...")
    return run_script(WEBSCRAPE_SCRIPT_PATH, "webscrape_runs.log")

def job_run_analyze_news():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Preparing to run analyze_news.py...")
    return run_script(ANALYZE_NEWS_SCRIPT_PATH, "analyze_news_runs.log")

def combined_pipeline_job():
    start_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{start_time_str}] Starting combined data pipeline...")
    success_webscrape = job_run_webscrape()
    if success_webscrape:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] webScrape.py ran successfully. Starting analyze_news.py...")
        job_run_analyze_news()
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] webScrape.py failed. Skipping analyze_news.py.")
    end_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{end_time_str}] Combined data pipeline finished.")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Next run scheduled in 25 minutes.")

schedule.every(25).minutes.do(combined_pipeline_job)

if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduler started.")
    print(f"PROJECT_MARKET_SENTIMENT_ROOT: {PROJECT_MARKET_SENTIMENT_ROOT}")
    print(f"Calculated PYTHON_EXECUTABLE: {PYTHON_EXECUTABLE}")
    print(f"Script WebScrape: {WEBSCRAPE_SCRIPT_PATH}")
    print(f"Script AnalyzeNews: {ANALYZE_NEWS_SCRIPT_PATH}")
    print("Scripts will run at the scheduled interval.")
    print("Press Ctrl+C to stop the scheduler.")

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Executing initial pipeline run...")
    combined_pipeline_job()

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduler stopped by user.")
    except Exception as e:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Unexpected error in scheduler loop: {e}")