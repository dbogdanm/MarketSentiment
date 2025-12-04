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
ALERT_MONITOR_SCRIPT_RELATIVE_PATH = os.path.join("website", "crucialPys", "alert_monitor.py")

WEBSCRAPE_SCRIPT_PATH = os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, WEBSCRAPE_SCRIPT_RELATIVE_PATH)
ANALYZE_NEWS_SCRIPT_PATH = os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, ANALYZE_NEWS_SCRIPT_RELATIVE_PATH)
ALERT_MONITOR_SCRIPT_PATH = os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, ALERT_MONITOR_SCRIPT_RELATIVE_PATH)

LOG_DIR = os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, "scheduler_logs")
os.makedirs(LOG_DIR, exist_ok=True)

def run_script(script_path, log_file_name):
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = os.path.join(LOG_DIR, log_file_name)
    script_basename = os.path.basename(script_path)
    
    try:
        if not os.path.exists(PYTHON_EXECUTABLE):
            raise FileNotFoundError(f"Python executable not found at: {PYTHON_EXECUTABLE}")
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found at: {script_path}")
            
        result = subprocess.run(
            [PYTHON_EXECUTABLE, script_path], check=True, capture_output=True, text=True,
            cwd=PROJECT_MARKET_SENTIMENT_ROOT, encoding='utf-8', errors='replace'
        )
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- Log at {current_time_str} for {script_basename} ---\nOutput:\n{result.stdout if result.stdout else 'N/A (No stdout)'}\n--- End Log ---\n\n")
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
        return False

    except FileNotFoundError as e:
        error_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- UNEXPECTED ERROR at {error_time_str} for {script_basename} ---\n")
            f.write(f"Error: {e}\n")
            f.write(f"Error Type: {type(e)}\n")
            f.write("\n--- End Error Log ---\n\n")
        return False

def job_run_webscrape():
    return run_script(WEBSCRAPE_SCRIPT_PATH, "webscrape_runs.log")

def job_run_analyze_news():
    return run_script(ANALYZE_NEWS_SCRIPT_PATH, "analyze_news_runs.log")

def job_run_alert_monitor():
    return run_script(ALERT_MONITOR_SCRIPT_PATH, "alert_monitor_runs.log")

def combined_pipeline_job():
    success_webscrape = job_run_webscrape()
    if success_webscrape:
        job_run_analyze_news()

schedule.every(25).minutes.do(combined_pipeline_job)
schedule.every(5).minutes.do(job_run_alert_monitor)

if __name__ == "__main__":
    combined_pipeline_job()
    job_run_alert_monitor()

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    except Exception:
        pass
