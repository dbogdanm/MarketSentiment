import schedule # importa biblioteca pentru a programa task-uri (sa ruleze la anumite intervale)
import time # importa biblioteca pentru functii legate de timp (ex: pauza)
import subprocess # importa biblioteca pentru a rula alte scripturi/programe
import os # importa biblioteca pentru a lucra cu sistemul de operare (ex: cai de fisiere)
from datetime import datetime # importa biblioteca pentru a lucra cu date si ore

# aflam calea absoluta catre directorul unde se gaseste acest script (scheduler_main.py)
# aceasta va fi considerata radacina proiectului nostru de sentiment de piata
PROJECT_MARKET_SENTIMENT_ROOT = os.path.dirname(os.path.abspath(__file__))

# calculam calea catre desktop, urcand doua niveluri din directorul proiectului
# aceasta presupune o anumita structura de directoare pe calculatorul tau
DESKTOP_PATH = os.path.abspath(os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, "..", ".."))

# definim numele folderelor relevante pentru mediul virtual python
PYTHON_PROJECT1_FOLDER_NAME = "PythonProject1"
VENV_FOLDER_NAME = ".venv1"
SCRIPTS_FOLDER_NAME = "Scripts" # pe windows, folderul este 'scripts'
PYTHON_EXE_NAME = "python.exe" # numele executabilului python

# construim calea completa catre executabilul python din mediul virtual
# aceasta este o cale importanta si trebuie sa fie corecta pentru sistemul tau
PYTHON_EXECUTABLE = os.path.join(
    DESKTOP_PATH,
    PYTHON_PROJECT1_FOLDER_NAME,
    VENV_FOLDER_NAME,
    SCRIPTS_FOLDER_NAME,
    PYTHON_EXE_NAME
)

# definim caile relative catre scripturile pe care vrem sa le rulam, pornind de la radacina proiectului
WEBSCRAPE_SCRIPT_RELATIVE_PATH = os.path.join("website", "crucialPys", "webScrape.py")
ANALYZE_NEWS_SCRIPT_RELATIVE_PATH = os.path.join("website", "crucialPys", "analyze_news.py")

# construim caile absolute complete catre scripturi
WEBSCRAPE_SCRIPT_PATH = os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, WEBSCRAPE_SCRIPT_RELATIVE_PATH)
ANALYZE_NEWS_SCRIPT_PATH = os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, ANALYZE_NEWS_SCRIPT_RELATIVE_PATH)

# definim calea catre directorul unde vom salva fisierele de log
LOG_DIR = os.path.join(PROJECT_MARKET_SENTIMENT_ROOT, "scheduler_logs")
os.makedirs(LOG_DIR, exist_ok=True) # cream directorul de loguri daca nu exista deja

def run_script(script_path, log_file_name):
    # functie pentru a rula un script python si a-i salva output-ul
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # luam data si ora curenta pentru log
    log_path = os.path.join(LOG_DIR, log_file_name) # calea completa catre fisierul de log specific
    script_basename = os.path.basename(script_path) # extragem doar numele fisierului scriptului

    print(f"[{current_time_str}] Starting script: {script_basename}") # mesaj in consola scheduler-ului
    try:
        # verificam daca executabilul python si scriptul tinta exista pe disc
        if not os.path.exists(PYTHON_EXECUTABLE):
            raise FileNotFoundError(f"Python executable not found at: {PYTHON_EXECUTABLE}")
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found at: {script_path}")

        # rulam scriptul specificat ca un proces separat
        result = subprocess.run(
            [PYTHON_EXECUTABLE, script_path], # comanda de executat (ex: "python.exe script.py")
            check=True,             # daca e true, ridica o exceptie 'CalledProcessError' daca scriptul esueaza (cod de retur non-zero)
            capture_output=True,    # vrem sa prindem ce afiseaza scriptul (stdout si stderr)
            text=True,              # vrem ca output-ul sa fie decodat ca text (string)
            cwd=PROJECT_MARKET_SENTIMENT_ROOT, # setam directorul de lucru curent la radacina proiectului
                                      # pentru ca scripturile apelate sa gaseasca fisierele relative corect
            encoding='utf-8',       # specificam codificarea pentru output-ul text
            errors='replace'        # daca sunt caractere in output pe care utf-8 nu le poate decoda,
                                      # le inlocuieste cu un caracter special (�) in loc sa crape
        )
        # daca am ajuns aici, scriptul a rulat si s-a terminat cu codul 0 (succes)
        with open(log_path, "a", encoding="utf-8") as f: # deschidem fisierul de log in mod 'append' (adaugare)
            f.write(f"--- Log at {current_time_str} for {script_basename} ---\n")
            f.write("Output:\n")
            f.write(result.stdout if result.stdout else "N/A (No stdout)\n") # scriem ce a afisat scriptul pe stdout
            # am putea adauga si result.stderr aici daca vrem sa logam si warning-urile chiar si la succes
            f.write("\n--- End Log ---\n\n")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Script {script_basename} finished successfully.")
        return True # indicam ca rularea a avut succes

    except subprocess.CalledProcessError as e:
        # aceasta exceptie este prinsa daca 'check=True' si scriptul returneaza un cod de eroare
        error_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- ERROR at {error_time_str} for {script_basename} ---\n")
            f.write(f"Return code: {e.returncode}\n")
            f.write("Stdout:\n")
            f.write(e.stdout if e.stdout else "N/A (No stdout)\n")
            f.write("\nStderr:\n")
            f.write(e.stderr if e.stderr else "N/A (No stderr)\n") # aici e mesajul de eroare al scriptului
            f.write("\n--- End Error Log ---\n\n")
        print(f"[{error_time_str}] ERROR running script {script_basename}. See {log_file_name}.")
        return False # indicam ca rularea a esuat
    except FileNotFoundError as e:
        # aceasta exceptie este prinsa daca PYTHON_EXECUTABLE sau script_path nu sunt gasite
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
        # prindem orice alta eroare neasteptata care ar putea aparea
        error_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{error_time_str}] An unexpected error occurred while running {script_basename}: {e}")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- UNEXPECTED ERROR at {error_time_str} for {script_basename} ---\n")
            f.write(f"Error: {e}\n")
            f.write(f"Error Type: {type(e)}\n")
            f.write("\n--- End Error Log ---\n\n")
        return False

def job_run_webscrape():
    # functie care defineste task-ul de rulare a scriptului webscrape
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Preparing to run webScrape.py...")
    return run_script(WEBSCRAPE_SCRIPT_PATH, "webscrape_runs.log") # apelam functia run_script

def job_run_analyze_news():
    # functie care defineste task-ul de rulare a scriptului analyze_news
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Preparing to run analyze_news.py...")
    return run_script(ANALYZE_NEWS_SCRIPT_PATH, "analyze_news_runs.log") # apelam functia run_script

def combined_pipeline_job():
    # functie care defineste un task combinat: ruleaza webscrape, si daca reuseste, ruleaza analyze_news
    start_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{start_time_str}] Starting combined data pipeline...")
    success_webscrape = job_run_webscrape() # rulam primul script
    if success_webscrape: # verificam daca primul script a rulat cu succes
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] webScrape.py ran successfully. Starting analyze_news.py...")
        job_run_analyze_news() # rulam al doilea script
    else: # daca primul script a esuat
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] webScrape.py failed. Skipping analyze_news.py.")
    end_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{end_time_str}] Combined data pipeline finished.")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Next run scheduled in 25 minutes.")

# programam task-ul combinat sa ruleze la fiecare 25 de minute
schedule.every(25).minutes.do(combined_pipeline_job)
# pentru testare, poti schimba la un interval mai mic:
# schedule.every(1).minutes.do(combined_pipeline_job) # la fiecare minut
# schedule.every(10).seconds.do(combined_pipeline_job) # la fiecare 10 secunde (foarte des)

# acest bloc de cod se executa doar daca scriptul este rulat direct (nu importat ca modul)
if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduler started.")
    print(f"PROJECT_MARKET_SENTIMENT_ROOT: {PROJECT_MARKET_SENTIMENT_ROOT}")
    print(f"Calculated PYTHON_EXECUTABLE: {PYTHON_EXECUTABLE}") # afisam calea calculata pentru python
    print(f"Script WebScrape: {WEBSCRAPE_SCRIPT_PATH}") # afisam calea catre script
    print(f"Script AnalyzeNews: {ANALYZE_NEWS_SCRIPT_PATH}") # afisam calea catre script
    print("Scripts will run at the scheduled interval.")
    print("Press Ctrl+C to stop the scheduler.")

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Executing initial pipeline run...")
    combined_pipeline_job() # rulam o data pipeline-ul la pornirea scheduler-ului

    try:
        while True: # o bucla care ruleaza la nesfarsit (pana la ctrl+c)
            schedule.run_pending() # verifica daca sunt task-uri programate care trebuie rulate
            time.sleep(1)          # face o pauza de o secunda pentru a nu suprasolicita procesorul
    except KeyboardInterrupt: # daca utilizatorul apasa ctrl+c in terminal
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduler stopped by user.")
    except Exception as e: # prinde orice alta eroare neprevazuta in bucla principala
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Unexpected error in scheduler loop: {e}")