from flask import Flask, render_template, Response, request, json, \
    jsonify  # importam diverse unelte din biblioteca flask
import os  # pentru a lucra cu sistemul de operare (cai, variabile de mediu)
import datetime  # pentru a lucra cu obiecte de tip data si ora
from datetime import timezone  # specific pentru timezone.utc (timpul universal coordonat)
import psycopg2  # biblioteca pentru a ne conecta la baza de date postgresql
from psycopg2.extras import RealDictCursor  # ca sa primim rezultatele din db ca dictionare (cheie: valoare)
import csv  # pentru a genera fisiere csv (pentru export)
import io  # pentru a lucra cu stream-uri de date in memorie (util pentru csv)
import markdown  # pentru a converti text formatat markdown in html (daca ai nevoie)
import subprocess  # pentru a rula alte scripturi python din acest script (cele de webscrape si analyze)

app = Flask(__name__)  # cream aplicatia noastra web flask

# --- configuratii pentru baza de date si aplicatie ---
# luam detaliile de conectare la baza de date din variabilele de mediu ale sistemului
# daca nu gaseste variabila de mediu, foloseste valoarea scrisa dupa virgula (ex: "localhost")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

# constante pentru a defini cate inregistrari vechi sa afisam
MAX_HISTORY_RECORDS_DISPLAY = 15  # pentru tabelul de pe pagina
MAX_HISTORY_RECORDS_CHART = 50  # pentru grafice

# --- cai pentru rularea scripturilor externe ---
# aflam calea absoluta catre directorul unde se gaseste acest fisier (appflask.py)
APP_DIR = os.path.dirname(os.path.abspath(__file__))
# mergem un nivel mai sus pentru a ajunge la radacina proiectului principal (ProiectMarketSentimentMDS)
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, ".."))

# incercam sa ghicim calea catre desktop, presupunand o anumita structura de directoare
# urcam doua niveluri din radacina proiectului
DESKTOP_PATH_GUESS = os.path.abspath(os.path.join(PROJECT_ROOT, "..", ".."))
PYTHON_PROJECT1_FOLDER_NAME = "PythonProject1"  # numele folderului care contine mediul virtual .venv1
VENV_FOLDER_NAME = ".venv1"  # numele mediului virtual

# construim calea completa catre executabilul python din mediul virtual
# aceasta cale este foarte importanta si trebuie sa fie corecta pentru calculatorul tau!
PYTHON_EXECUTABLE = os.path.join(
    DESKTOP_PATH_GUESS,
    PYTHON_PROJECT1_FOLDER_NAME,
    VENV_FOLDER_NAME,
    "Scripts",  # pe windows, folderul cu executabilele python din venv se numeste 'scripts'
    "python.exe"  # numele executabilului python
)
# daca mediul tau virtual (.venv1) este direct in folderul proiectului tau (ProiectMarketSentimentMDS),
# atunci linia de mai sus ar trebui sa fie:
# PYTHON_EXECUTABLE = os.path.join(PROJECT_ROOT, ".venv1", "Scripts", "python.exe")


# definim caile complete catre scripturile webscrape.py si analyze_news.py
WEBSCRAPE_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "website", "crucialPys", "webScrape.py")
ANALYZE_NEWS_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "website", "crucialPys", "analyze_news.py")


# --- sfarsit cai ---


def get_db_connection():
    """functie care incearca sa se conecteze la baza de date postgresql si returneaza conexiunea."""
    # verificam daca avem toate detaliile necesare (nume db, user, parola)
    if not all([DB_NAME, DB_USER, DB_PASS]):
        print("Error: Database credentials missing.")  # mesaj de eroare daca lipsesc
        return None  # returnam nimic, pentru ca nu ne putem conecta
    try:
        # incercam sa cream conexiunea
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        print("Successfully connected to PostgreSQL database.")  # mesaj de succes
        return conn  # returnam obiectul de conexiune
    except (Exception, psycopg2.DatabaseError) as error:  # prindem orice eroare de conectare
        print(f"Error connecting to PostgreSQL database: {error}")  # afisam eroarea
        return None  # returnam nimic


def get_sentiment_data_from_db(limit_display=MAX_HISTORY_RECORDS_DISPLAY,
                               limit_chart=MAX_HISTORY_RECORDS_CHART,
                               for_export=False,  # un indicator (flag) sa stim daca datele sunt pentru export
                               start_date_str=None,  # data de inceput pentru filtrare (ca text)
                               end_date_str=None):  # data de sfarsit pentru filtrare (ca text)
    """
    functie complexa care preia toate datele de sentiment din baza de date.
    le proceseaza pentru a fi afisate pe pagina web (in tabel, grafice, sumar ai)
    si, de asemenea, pentru a fi exportate in format csv.
    accepta parametri pentru a limita numarul de inregistrari si pentru a filtra dupa data.
    """
    # initializam un dictionar cu valori default pentru cele mai recente date afisate
    latest_data = {
        "fear_greed": 50, "vix": None, "timestamp": "N/A", "summary_text": "N/A",  # valori brute
        "fear_greed_display": 50, "vix_display": "N/A", "last_updated": "N/A",  # valori formatate pentru afisare
        "summary_text_display": "<p>No AI summary currently available.</p>"  # mesaj default pentru sumar
    }
    # initializam listele unde vom stoca datele istorice prelucrate
    historical_data_raw = []  # lista pentru datele istorice brute din db
    history_for_table = []  # lista pentru datele formatate pentru tabelul de pe pagina
    history_timestamps = []  # lista pentru timestamp-urile din grafic
    history_fg_values = []  # lista pentru valorile fear & greed din grafic
    history_vix_values = []  # lista pentru valorile vix din grafic
    # history_table_raw_for_export va fi populat cu historical_data_raw

    conn = get_db_connection()  # obtinem o conexiune la baza de date

    if conn:  # continuam doar daca am reusit sa ne conectam
        try:
            # 'with conn.cursor(...)' se asigura ca cursorul este inchis automat la final
            # 'RealDictCursor' face ca fiecare rand din baza de date sa fie returnat ca un dictionar python
            # (ex: {'nume_coloana': valoare_coloana}) in loc de un tuplu
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # --- preluam cele mai recente date (ultimul rand inserat) ---
                cur.execute(
                    "SELECT fear_greed, vix, summary_text, timestamp FROM sentiment_history ORDER BY timestamp DESC LIMIT 1")
                latest_row = cur.fetchone()  # luam primul (si singurul) rand rezultat
                if latest_row:  # daca am gasit un rand
                    latest_data.update(latest_row)  # actualizam dictionarul 'latest_data' cu valorile din baza de date
                    print(f"Fetched latest data: {latest_row}")

                # --- procesam datele recente pentru a fi afisate corect ---
                # verificam si formatam valoarea fear & greed
                if latest_data.get("fear_greed") is None or \
                        not isinstance(latest_data.get("fear_greed"), (int, float)) or \
                        not (0 <= latest_data.get("fear_greed",
                                                  50) <= 100):  # .get cu default previne eroare daca cheia lipseste
                    latest_data["fear_greed_display"] = 50  # valoare default pentru indicatorul gauge
                else:
                    latest_data["fear_greed_display"] = latest_data["fear_greed"]

                # verificam si formatam valoarea vix
                if latest_data.get("vix") is None:
                    latest_data["vix_display"] = "N/A"
                else:
                    try:
                        latest_data["vix_display"] = f"{float(latest_data['vix']):.2f}"  # formatam cu 2 zecimale
                    except (ValueError, TypeError):  # daca nu e un numar valid
                        latest_data["vix_display"] = "N/A"

                # formatam timestamp-ul pentru "analysis last updated"
                ts_latest = latest_data.get("timestamp")
                if isinstance(ts_latest, datetime.datetime):  # verificam daca e un obiect datetime valid
                    # daca are informatii despre fusul orar, le folosim, altfel adaugam 'utc' manual
                    latest_data["last_updated"] = ts_latest.strftime(
                        '%Y-%m-%d %H:%M:%S %Z') if ts_latest.tzinfo else ts_latest.strftime('%Y-%m-%d %H:%M:%S UTC')
                elif isinstance(ts_latest, str) and ts_latest != "N/A":  # cazul mai putin probabil cand e deja string
                    latest_data["last_updated"] = ts_latest
                else:  # daca nu avem un timestamp valid
                    latest_data["last_updated"] = "N/A"

                # pregatim sumarul ai pentru afisare
                raw_summary = latest_data.get("summary_text")
                if not raw_summary or raw_summary.strip() == "N/A":  # daca e gol sau "n/a"
                    latest_data["summary_text_display"] = "<p>No AI summary currently available.</p>"  # mesaj default
                else:
                    # presupunem ca ai-ul nu returneaza formatare markdown, deci folosim textul brut.
                    # in html, vom folosi css 'white-space: pre-wrap' pentru a respecta newline-urile.
                    latest_data["summary_text_display"] = raw_summary

                # --- preluam datele istorice (pentru tabel si grafice) ---
                query_params = []  # lista pentru parametrii query-ului sql (pentru siguranta impotriva sql injection)
                sql_history_base = "SELECT id, fear_greed, vix, summary_text, timestamp FROM sentiment_history"  # query-ul de baza
                conditions = []  # lista pentru conditiile 'where' (filtrele de data)

                # daca am primit o data de inceput pentru filtru
                if start_date_str:
                    try:
                        # convertim string-ul (ex: "2023-10-26") intr-un obiect datetime
                        # setam ora la inceputul zilei (00:00:00) si fusul orar la utc
                        start_date_obj = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').replace(hour=0,
                                                                                                        minute=0,
                                                                                                        second=0,
                                                                                                        microsecond=0,
                                                                                                        tzinfo=timezone.utc)
                        conditions.append("timestamp >= %s")  # adaugam conditia la lista
                        query_params.append(start_date_obj)  # adaugam valoarea la lista de parametri
                    except ValueError:  # daca formatul datei e gresit
                        print(f"Warning: Invalid start_date format: {start_date_str}")

                # similar pentru data de sfarsit, setam ora la sfarsitul zilei (23:59:59)
                if end_date_str:
                    try:
                        end_date_obj = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59,
                                                                                                    second=59,
                                                                                                    microsecond=999999,
                                                                                                    tzinfo=timezone.utc)
                        conditions.append("timestamp <= %s")
                        query_params.append(end_date_obj)
                    except ValueError:
                        print(f"Warning: Invalid end_date format: {end_date_str}")

                # construim clauza 'where' daca avem conditii
                sql_where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
                # query-ul complet, ordonat descrescator dupa timestamp (cele mai noi primele)
                sql_history_ordered = sql_history_base + sql_where_clause + " ORDER BY timestamp DESC"

                # stabilim cate inregistrari sa luam din baza de date
                limit_for_query = limit_chart  # implicit, luam destule pentru grafic (care e de obicei mai mult decat pentru tabel)
                if for_export:  # daca este pentru exportul csv, vrem toate datele (fara limita)
                    limit_for_query = None

                sql_final_history = sql_history_ordered
                if limit_for_query is not None:  # daca avem o limita, o adaugam la query-ul sql
                    sql_final_history += " LIMIT %s"
                    query_params.append(limit_for_query)

                cur.execute(sql_final_history, tuple(query_params))  # executam query-ul final cu parametrii
                historical_data_raw = cur.fetchall()  # preluam toate randurile rezultate
                # historical_data_raw va fi folosit si pentru exportul csv, deoarece contine toate datele (daca for_export=true)
                # sau datele limitate pentru grafic
                print(f"Fetched {len(historical_data_raw)} historical records.")

                # procesam datele pentru grafic (chart)
                # pentru grafic, vrem datele de la cel mai vechi la cel mai nou
                data_for_chart_processing = list(historical_data_raw)  # facem o copie a listei
                # daca nu e pentru export si avem mai multe date decat limita pentru chart, le taiem
                if len(data_for_chart_processing) > limit_chart and not for_export:
                    data_for_chart_processing = data_for_chart_processing[:limit_chart]
                data_for_chart_processing.reverse()  # inversam ordinea (cel mai vechi primul)

                for record in data_for_chart_processing:
                    ts, fg, vix_val = record.get("timestamp"), record.get("fear_greed"), record.get("vix")
                    # formatam timestamp-ul pentru afisare pe axa x a graficului
                    history_timestamps.append(
                        ts.strftime('%Y-%m-%d %H:%M') if isinstance(ts, datetime.datetime) else "Invalid Date")
                    history_fg_values.append(
                        fg if isinstance(fg, (int, float)) else None)  # none daca valoarea lipseste
                    try:
                        history_vix_values.append(float(vix_val) if vix_val is not None else None)
                    except (ValueError, TypeError):  # in caz ca vix_val nu e numar
                        history_vix_values.append(None)

                # procesam datele pentru tabelul de pe pagina
                # historical_data_raw este deja sortat descrescator (cele mai noi primele)
                # luam doar primele 'limit_display' inregistrari pentru tabel
                for i, record_raw in enumerate(historical_data_raw):
                    if i >= limit_display and not for_export:  # aplicam limita doar daca nu e pentru export
                        break  # oprim bucla daca am atins limita
                    record_for_table = record_raw.copy()  # lucram pe o copie
                    ts_table = record_for_table.get("timestamp")
                    # formatam datele pentru afisare in tabel
                    record_for_table["timestamp_display"] = ts_table.strftime('%Y-%m-%d %H:%M') if isinstance(ts_table,
                                                                                                              datetime.datetime) else "N/A"
                    record_for_table["fear_greed_display"] = record_for_table.get("fear_greed", "N/A")
                    try:
                        record_for_table[
                            "vix_display"] = f"{float(record_for_table.get('vix', 0.0)):.2f}" if record_for_table.get(
                            "vix") is not None else "N/A"
                    except (ValueError, TypeError):
                        record_for_table["vix_display"] = "N/A"
                    history_for_table.append(record_for_table)  # adaugam la lista pentru tabel
        except (Exception, psycopg2.DatabaseError) as error:  # prindem erori la interogarea bazei de date
            print(f"Error querying database: {error}")
        finally:  # acest bloc se executa intotdeauna, indiferent de erori
            if conn: conn.close(); print("Database connection closed.")  # inchidem conexiunea daca a fost deschisa
    else:  # daca nu am reusit sa ne conectam la db de la inceput
        print("Could not establish DB connection.")

    # returnam un dictionar care contine toate datele procesate
    return {
        "latest": latest_data, "history_table": history_for_table,
        "chart_data": {"timestamps": history_timestamps, "fg_values": history_fg_values,
                       "vix_values": history_vix_values},
        "history_table_raw_for_export": historical_data_raw  # datele brute pentru export
    }


@app.route('/')  # definim ruta principala a aplicatiei (ex: http://127.0.0.1:5000/)
def index():
    """aceasta functie este apelata cand un utilizator acceseaza pagina principala."""
    start_date = request.args.get('start_date')  # preluam parametrul 'start_date' din url (daca exista)
    end_date = request.args.get('end_date')  # preluam parametrul 'end_date' din url

    # apelam functia care ia datele din db, pasand si filtrele de data
    processed_data = get_sentiment_data_from_db(start_date_str=start_date, end_date_str=end_date)

    # trimitem datele catre fisierul html (template) pentru a fi afisate
    return render_template('index.html',
                           fear_greed_value=processed_data["latest"]["fear_greed_display"],
                           vix_value=processed_data["latest"]["vix_display"],
                           last_updated=processed_data["latest"]["last_updated"],
                           latest_summary=processed_data["latest"]["summary_text_display"],
                           history=processed_data.get("history_table", []),
                           # folosim .get pentru a evita eroare daca cheia lipseste
                           chart_timestamps=json.dumps(processed_data.get("chart_data", {}).get("timestamps", [])),
                           # convertim listele in json pentru javascript
                           chart_fg_values=json.dumps(processed_data.get("chart_data", {}).get("fg_values", [])),
                           chart_vix_values=json.dumps(processed_data.get("chart_data", {}).get("vix_values", [])),
                           current_start_date=start_date,
                           # trimitem inapoi filtrele pentru a le afisa in casutele de data
                           current_end_date=end_date)


@app.route('/export/csv')  # definim o ruta pentru a descarca datele ca fisier csv
def export_csv():
    """genereaza si ofera la descarcare un fisier csv cu istoricul datelor."""
    start_date = request.args.get('start_date')  # preluam filtrele de data din url
    end_date = request.args.get('end_date')

    # cerem toate datele din db (for_export=true), aplicand filtrele de data
    data_dict = get_sentiment_data_from_db(for_export=True, start_date_str=start_date, end_date_str=end_date)
    history_list_raw = data_dict.get("history_table_raw_for_export", [])  # luam datele brute

    if not history_list_raw:  # daca nu sunt date de exportat
        return "No data to export for the selected criteria.", 404  # returnam un mesaj de eroare

    output_stream = io.stringio()  # cream un buffer in memorie pentru a scrie csv-ul
    csv_writer = csv.writer(output_stream)  # initializam un scriitor csv

    headers = ["timestamp", "fear_greed", "vix", "summary_text"]  # definim capul de tabel pentru csv
    csv_writer.writerow(headers)  # scriem capul de tabel

    for record in history_list_raw:  # parcurgem fiecare inregistrare
        ts_obj = record.get("timestamp")
        ts_str = (ts_obj.strftime('%y-%m-%d %h:%m:%s %z') if ts_obj.tzinfo else ts_obj.strftime(
            '%y-%m-%d %h:%m:%s utc')) if isinstance(ts_obj, datetime.datetime) else ""
        summary = record.get("summary_text", "")
        # eliminam caracterele newline din sumar, ca sa nu strice formatul csv
        summary_cleaned = summary.replace('\r\n', ' ').replace('\n', ' ') if summary else ""
        # scriem un rand in csv cu datele din inregistrare
        csv_writer.writerow([ts_str, record.get("fear_greed", ""), record.get("vix", ""), summary_cleaned])

    csv_output = output_stream.getvalue()  # luam tot continutul csv ca un singur string
    output_stream.close()  # inchidem buffer-ul din memorie

    # cream un raspuns http care va face browserul sa descarce fisierul
    return Response(csv_output, mimetype="text/csv",
                    headers={"content-disposition": "attachment;filename=sentiment_history.csv"})


def execute_script_on_server(script_path):
    """functie ajutatoare pentru a rula un script python (webscrape sau analyze_news) pe server."""
    try:
        print(f"Attempting to run script: {script_path} with python: {PYTHON_EXECUTABLE}")
        # verificam daca executabilul python si scriptul tinta exista
        if not os.path.exists(PYTHON_EXECUTABLE): return {"status": "error",
                                                          "message": f"Python executable not found: {PYTHON_EXECUTABLE}"}, 500
        if not os.path.exists(script_path): return {"status": "error",
                                                    "message": f"Script not found: {script_path}"}, 500

        # rulam scriptul ca un proces separat si asteptam sa se termine
        process = subprocess.run(
            [PYTHON_EXECUTABLE, script_path],  # comanda de rulat
            capture_output=True, text=True, check=False,  # setari pentru a prinde output-ul si a nu crapa la erori
            cwd=PROJECT_ROOT, encoding='utf-8', errors='replace'
            # directorul de lucru si gestionarea erorilor de encoding
        )
        # verificam codul de retur al scriptului
        if process.returncode == 0:  # 0 inseamna succes
            msg = f"Script {os.path.basename(script_path)} executed successfully."
            print(msg, "\nStdout:", process.stdout)  # afisam in consola serverului ce a printat scriptul
            return {"status": "success", "message": msg, "output": process.stdout}, 200  # returnam succes si output-ul
        else:  # daca scriptul a esuat
            msg = f"Script {os.path.basename(script_path)} failed (code {process.returncode})."
            print(msg, "\nStderr:", process.stderr, "\nStdout:", process.stdout)  # afisam erorile si output-ul
            return {"status": "error", "message": msg, "error_output": process.stderr, "output": process.stdout}, 500
    except Exception as e:  # prindem orice alta exceptie neasteptata
        msg = f"Exception running {os.path.basename(script_path)}: {str(e)}"
        print(msg)
        return {"status": "error", "message": msg}, 500


@app.route('/run_webscrape', methods=['post'])  # definim o ruta care accepta doar request-uri post
def run_webscrape_route():
    """ruta apelata de butonul 'run scraper' din interfata web."""
    print("Request to run webScrape.py")
    result, status_code = execute_script_on_server(WEBSCRAPE_SCRIPT_PATH)  # rulam scriptul
    return jsonify(result), status_code  # returnam raspunsul ca json


@app.route('/run_analyze_news', methods=['post'])
def run_analyze_news_route():
    """ruta apelata de butonul 'run analyzer' din interfata web."""
    print("Request to run analyze_news.py")
    result, status_code = execute_script_on_server(ANALYZE_NEWS_SCRIPT_PATH)
    return jsonify(result), status_code


@app.route('/run_pipeline', methods=['post'])
def run_pipeline_route():
    """ruta apelata de butonul 'refresh all data' care ruleaza ambele scripturi."""
    print("Request to run full data pipeline.")
    results, overall_status = [], "success"  # initializam pentru a stoca rezultatele pasilor

    # pasul 1: rulam webscrape.py
    result_scrape, status_scrape = execute_script_on_server(WEBSCRAPE_SCRIPT_PATH)
    results.append({"script": "webScrape.py", **result_scrape})  # adaugam rezultatul la lista
    if status_scrape != 200:  # daca webscrape a esuat
        overall_status = "error"  # marcam ca intregul pipeline a esuat
        msg = "WebScrape failed. Analyze News script skipped."
        print(msg)
        results.append({"script": "analyze_news.py", "status": "skipped",
                        "message": msg})  # adaugam un mesaj ca al doilea script a fost sarit
        return jsonify({"status": overall_status, "pipeline_results": results}), 500  # returnam eroare

    # pasul 2: rulam analyze_news.py (doar daca webscrape a reusit)
    print("WebScrape successful, proceeding to Analyze News.")
    result_analyze, status_analyze = execute_script_on_server(ANALYZE_NEWS_SCRIPT_PATH)
    results.append({"script": "analyze_news.py", **result_analyze})
    if status_analyze != 200:  # daca analyze_news a esuat
        overall_status = "error"

    final_msg = "Data pipeline finished." + (" with errors." if overall_status == "error" else "")  # mesaj final
    return jsonify({"status": overall_status, "message": final_msg,
                    "pipeline_results": results}), 200 if overall_status == "success" else 500


# acest bloc se executa doar cand rulezi direct 'python appflask.py'
if __name__ == '__main__':
    app.config[
        'templates_auto_reloader'] = True  # util pentru dezvoltare, face ca flask sa reincarce template-urile html la fiecare modificare
    app.run(
        debug=True)  # porneste serverul web flask. debug=true afiseaza erori detaliate in browser si reincarca serverul la modificari in codul python.