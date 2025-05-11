# scheduler_main.py
import schedule # importa biblioteca pentru a programa task-uri (sa ruleze la anumite intervale)
import time # importa biblioteca pentru functii legate de timp (ex: pauza)
import subprocess # importa biblioteca pentru a rula alte scripturi/programe
import os # importa biblioteca pentru a lucra cu sistemul de operare (ex: cai de fisiere)
from datetime import datetime # importa biblioteca pentru a lucra cu date si ore

# project_market_sentiment_root este calea catre directorul unde se afla acest script (scheduler_main.py)
# aceasta este considerata radacina proiectului
PROJECT_MARKET_SENTIMENT_ROOT = os.path.dirname(os.path.abspath(__file__))

# calculam calea catre desktop, urcand doua niveluri din directorul proiectului
# aceasta presupune ca folderul proiectului este intr-un alt folder pe desktop
DESKTOP_PATH = os.path.abspath(os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, "..", ".."))

# definim numele folderelor relevante pentru mediul virtual python
PYTHON_PROJECT1_FOLDER_NAME = "PythonProject1" # numele folderului care contine .venv1
VENV_FOLDER_NAME = ".venv1" # numele mediului virtual
SCRIPTS_FOLDER_NAME = "Scripts" # pe windows, folderul cu executabilele python din venv
PYTHON_EXE_NAME = "python.exe" # numele executabilului python

# construim calea completa catre executabilul python din mediul virtual
# aceasta cale trebuie sa fie corecta pentru sistemul tau pentru ca scripturile sa ruleze
PYTHON_EXECUTABLE = os.path.join(
    DESKTOP_PATH,
    PYTHON_PROJECT1_FOLDER_NAME,
    VENV_FOLDER_NAME,
    SCRIPTS_FOLDER_NAME,
    PYTHON_EXE_NAME
)

# definim caile relative catre scripturile pe care vrem sa le rulam
WEBSCRAPE_SCRIPT_RELATIVE_PATH = os.path.join("website", "crucialPys", "webScrape.py")
ANALYZE_NEWS_SCRIPT_RELATIVE_PATH = os.path.join("website", "crucialPys", "analyze_news.py")
# calea corectata pentru alert_monitor.py, presupunand ca este in website/crucialpys
ALERT_MONITOR_SCRIPT_RELATIVE_PATH = os.path.join("website", "crucialPys", "alert_monitor.py")

# construim caile absolute complete catre scripturi, bazate pe radacina proiectului
WEBSCRAPE_SCRIPT_PATH = os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, WEBSCRAPE_SCRIPT_RELATIVE_PATH)
ANALYZE_NEWS_SCRIPT_PATH = os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, ANALYZE_NEWS_SCRIPT_RELATIVE_PATH)
ALERT_MONITOR_SCRIPT_PATH = os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, ALERT_MONITOR_SCRIPT_RELATIVE_PATH)

# definim calea catre directorul unde vom salva fisierele de log
LOG_DIR = os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, "scheduler_logs")
os.makedirs(LOG_DIR, exist_ok=True) # cream directorul de loguri daca nu exista deja

# functie pentru a rula un script python si a-i salva output-ul
def run_script(script_path, log_file_name):
    # ... (codul functiei run_script existent, cu comentariile adaugate anterior) ...
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = os.path.join(LOG_DIR, log_file_name)
    script_basename = os.path.basename(script_path)
    print(f"[{current_time_str}] Starting script: {script_basename}")
    try:
        if not os.path.exists(PYTHON_EXECUTABLE): raise FileNotFoundError(f"Python executable not found at: {PYTHON_EXECUTABLE}")
        if not os.path.exists(script_path): raise FileNotFoundError(f"Script not found at: {script_path}")
        result = subprocess.run(
            [PYTHON_EXECUTABLE, script_path], check=True, capture_output=True, text=True,
            cwd=PROJECT_MARKET_SENTIMENT_ROOT, encoding='utf-8', errors='replace'
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- Log at {current_time_str} for {script_basename} ---\nOutput:\n{result.stdout if result.stdout else 'N/A (No stdout)'}\n--- End Log ---\n\n")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Script {script_basename} finished successfully.")
        return True
    except subprocess.CalledProcessError as e:
        # ... (logica de eroare existenta)
        # scriem detaliile erorii in fisierul de log
        error_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- ERROR at {error_time_str} for {script_basename} ---\n")
            f.write(f"Return code: {e.returncode}\n")
            f.write("Stdout:\n")
            f.write(e.stdout if e.stdout else "N/A (No stdout)\n")
            f.write("\nStderr:\n")
            f.write(e.stderr if e.stderr else "N/A (No stderr)\n")
            f.write("\n--- End Error Log ---\n\n")
        print(f"ERROR running script {script_basename}. See {log_file_name}.")
        return False
    except FileNotFoundError as e:
        # ... (logica de eroare existenta)
        error_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- FATAL ERROR at {error_time_str} for {script_basename} ---\n")
            f.write(f"{e}\n")
            f.write(f"Check PYTHON_EXECUTABLE and script_path paths.\n")
            f.write(f"PYTHON_EXECUTABLE: {PYTHON_EXECUTABLE}\n")
            f.write(f"Script Path: {script_path}\n")
            f.write("\n--- End Error Log ---\n\n")
        print(f"FATAL ERROR: {e}")
        return False
    except Exception as e:
        # ... (logica de eroare existenta) ...
        error_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- UNEXPECTED ERROR at {error_time_str} for {script_basename} ---\n")
            f.write(f"Error: {e}\n")
            f.write(f"Error Type: {type(e)}\n")
            f.write("\n--- End Error Log ---\n\n")
        print(f"An unexpected error occurred while running {script_basename}: {e}")
        return False

def job_run_webscrape():
    # functie care defineste un o sarcina pentru a rula scriptul webscrape
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Preparing to run webScrape.py...")
    return run_script(WEBSCRAPE_SCRIPT_PATH, "webscrape_runs.log") # apeleaza functia run_script

def job_run_analyze_news():
    # functie care defineste un "job" pentru a rula scriptul analyze_news
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Preparing to run analyze_news.py...")
    return run_script(ANALYZE_NEWS_SCRIPT_PATH, "analyze_news_runs.log")

def job_run_alert_monitor():
    # functie care defineste un "job" pentru a rula scriptul alert_monitor
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Preparing to run alert_monitor.py...")
    return run_script(ALERT_MONITOR_SCRIPT_PATH, "alert_monitor_runs.log") # foloseste calea corectata



def combined_pipeline_job(): # acest job ruleaza doar webscrape si analyze_news
    # functie care defineste un task combinat: ruleaza webscrape, si daca reuseste, ruleaza analyze_news
    start_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{start_time_str}] Starting combined data pipeline (webScrape & analyzeNews)...")
    success_webscrape = job_run_webscrape() # rulam primul script
    if success_webscrape: # verificam daca primul script a rulat cu succes
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] webScrape.py ran successfully. Starting analyze_news.py...")
        job_run_analyze_news() # rulam al doilea script
    else: # daca primul script a esuat
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] webScrape.py failed. Skipping analyze_news.py.")
    end_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{end_time_str}] Combined data pipeline (webScrape & analyzeNews) finished.")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Next data pipeline run scheduled in approximately 25 minutes.")

# programam task-ul combinat (webscrape + analyze_news) sa ruleze la fiecare 25 de minute
schedule.every(25).minutes.do(combined_pipeline_job)
# programam task-ul pentru monitorul de alerte sa ruleze la fiecare 5 minute
schedule.every(5).minutes.do(job_run_alert_monitor)


# acest bloc de cod se executa doar daca scriptul este rulat direct (nu importat ca modul)
if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduler started.")
    print(f"PROJECT_MARKET_SENTIMENT_ROOT: {PROJECT_MARKET_SENTIMENT_ROOT}")
    print(f"Calculated PYTHON_EXECUTABLE: {PYTHON_EXECUTABLE}") # afisam calea calculata pentru python
    print(f"Script WebScrape: {WEBSCRAPE_SCRIPT_PATH}") # afisam calea catre script
    print(f"Script AnalyzeNews: {ANALYZE_NEWS_SCRIPT_PATH}") # afisam calea catre script
    print(f"Script AlertMonitor: {ALERT_MONITOR_SCRIPT_PATH}") # afisam calea catre scriptul de alerte
    print("Scripts will run at their respective scheduled intervals.")
    print("Press Ctrl+C to stop the scheduler.")

    # rulam o data fiecare job la pornirea scheduler-ului, sa nu asteptam primul interval
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Executing initial pipeline run...")
    combined_pipeline_job()
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Executing initial alert monitor run...")
    job_run_alert_monitor()

    try:
        while True: # o bucla care ruleaza la nesfarsit (pana la ctrl+c)
            schedule.run_pending() # verifica daca sunt task-uri programate care trebuie rulate
            time.sleep(1)          # face o pauza de o secunda pentru a nu suprasolicita procesorul
    except KeyboardInterrupt: # daca utilizatorul apasa ctrl+c in terminal
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduler stopped by user.")
    except Exception as e: # prinde orice alta eroare neprevazuta in bucla principala
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Unexpected error in scheduler loop: {e}")