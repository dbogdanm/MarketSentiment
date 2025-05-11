from flask import Flask, render_template, Response, request, json, jsonify, redirect, url_for, \
    flash  # importam uneltele necesare din flask
import os  # pentru a lucra cu sistemul de operare
import datetime  # pentru a lucra cu date si ore
from datetime import timezone  # pentru fusul orar utc
import psycopg2  # pentru conectarea la postgresql
from psycopg2.extras import RealDictCursor  # pentru a primi rezultate ca dictionare
import csv  # pentru generarea fisierelor csv
import io  # pentru lucrul cu stream-uri in memorie
# import markdown
import subprocess  # pentru a rula scripturile externe

from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField
from wtforms.validators import DataRequired, Email, NumberRange  # unelte pentru a valida datele din formular


app = Flask(__name__)  # initializam aplicatia flask

# !!! important: seteaza o cheie secreta pentru protectia csrf (cross-site request forgery) !!!
# intr-o aplicatie reala, aceasta ar trebui sa fie o valoare complexa si stocata intr-o variabila de mediu.
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'o_cheie_secreta_foarte_puternica_si_aleatorie_123!')


# --- definirea formularului flask-wtf pentru subscrierea la alerte vix ---
class VixAlertSubscriptionForm(FlaskForm):
    # definim campul pentru email, cu validatori: obligatoriu si format de email valid
    email = StringField('Email Address', validators=[DataRequired(message="Email is required."),
                                                     Email(message="Invalid email address.")])
    # definim campul pentru pragul vix, cu validatori: obligatoriu si un numar pozitiv
    vix_threshold = FloatField('VIX Threshold', validators=[DataRequired(message="VIX threshold is required."),
                                                            NumberRange(min=0,
                                                                        message="Threshold must be a non-negative number.")])
    # definim butonul de submit al formularului
    submit = SubmitField('Subscribe / Update Alert')


# --- sfarsit definire formular ---


# --- configuratii pentru baza de date si aplicatie (raman la fel) ---
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

MAX_HISTORY_RECORDS_DISPLAY = 15
MAX_HISTORY_RECORDS_CHART = 50

# --- cai pentru rularea scripturilor externe (raman la fel) ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, ".."))
DESKTOP_PATH_GUESS = os.path.abspath(os.path.join(PROJECT_ROOT, "..", ".."))
PYTHON_PROJECT1_FOLDER_NAME = "PythonProject1"
VENV_FOLDER_NAME = ".venv1"
PYTHON_EXECUTABLE = os.path.join(DESKTOP_PATH_GUESS, PYTHON_PROJECT1_FOLDER_NAME, VENV_FOLDER_NAME, "Scripts",
                                 "python.exe")
# PYTHON_EXECUTABLE = r"C:\Users\ripip\Desktop\PythonProject1\.venv1\Scripts\python.exe" # alternativa hardcodata
WEBSCRAPE_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "website", "crucialPys", "webScrape.py")
ANALYZE_NEWS_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "website", "crucialPys", "analyze_news.py")


def get_db_connection():
    """functie care incearca sa se conecteze la baza de date postgresql si returneaza conexiunea."""
    if not all([DB_NAME, DB_USER, DB_PASS]):
        print("Error: Database credentials missing.")  # print in engleza
        return None
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        print("Successfully connected to PostgreSQL database.")  # print in engleza
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error connecting to PostgreSQL database: {error}")  # print in engleza
        return None


def get_sentiment_data_from_db(limit_display=MAX_HISTORY_RECORDS_DISPLAY,
                               limit_chart=MAX_HISTORY_RECORDS_CHART,
                               for_export=False,
                               start_date_str=None,
                               end_date_str=None):
    """
    preia datele de sentiment din baza de date, le proceseaza pentru afisare si export.
    """
    latest_data = {
        "fear_greed": 50, "vix": None, "timestamp": "N/A", "summary_text": "N/A",
        "fear_greed_display": 50, "vix_display": "N/A", "last_updated": "N/A",
        "summary_text_display": "No AI summary currently available."  # mesaj default in engleza
    }
    historical_data_raw, history_for_table, history_timestamps, history_fg_values, history_vix_values = [], [], [], [], []

    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT fear_greed, vix, summary_text, timestamp FROM sentiment_history ORDER BY timestamp DESC LIMIT 1")
                latest_row = cur.fetchone()
                if latest_row:
                    latest_data.update(latest_row)
                    print(f"Fetched latest data: {latest_row}")  # print in engleza

                if latest_data.get("fear_greed") is None or \
                        not isinstance(latest_data.get("fear_greed"), (int, float)) or \
                        not (0 <= latest_data.get("fear_greed", 50) <= 100):
                    latest_data["fear_greed_display"] = 50
                else:
                    latest_data["fear_greed_display"] = latest_data["fear_greed"]

                if latest_data.get("vix") is None:
                    latest_data["vix_display"] = "N/A"
                else:
                    try:
                        latest_data["vix_display"] = f"{float(latest_data['vix']):.2f}"
                    except (ValueError, TypeError):
                        latest_data["vix_display"] = "N/A"

                ts_latest = latest_data.get("timestamp")
                if isinstance(ts_latest, datetime.datetime):
                    latest_data["last_updated"] = ts_latest.strftime(
                        '%Y-%m-%d %H:%M:%S %Z') if ts_latest.tzinfo else ts_latest.strftime('%Y-%m-%d %H:%M:%S UTC')
                elif isinstance(ts_latest, str) and ts_latest != "N/A":
                    latest_data["last_updated"] = ts_latest
                else:
                    latest_data["last_updated"] = "N/A"

                raw_summary = latest_data.get("summary_text")
                if not raw_summary or raw_summary.strip() == "N/A":
                    latest_data["summary_text_display"] = "No AI summary currently available."  # mesaj in engleza
                else:
                    latest_data["summary_text_display"] = raw_summary  # text simplu, nu markdown

                query_params, conditions = [], []
                sql_history_base = "SELECT id, fear_greed, vix, summary_text, timestamp FROM sentiment_history"
                if start_date_str:
                    try:
                        start_date_obj = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').replace(hour=0,
                                                                                                        minute=0,
                                                                                                        second=0,
                                                                                                        microsecond=0,
                                                                                                        tzinfo=timezone.utc)
                        conditions.append("timestamp >= %s");
                        query_params.append(start_date_obj)
                    except ValueError:
                        print(f"Warning: Invalid start_date format: {start_date_str}")  # print in engleza
                if end_date_str:
                    try:
                        end_date_obj = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59,
                                                                                                    second=59,
                                                                                                    microsecond=999999,
                                                                                                    tzinfo=timezone.utc)
                        conditions.append("timestamp <= %s");
                        query_params.append(end_date_obj)
                    except ValueError:
                        print(f"Warning: Invalid end_date format: {end_date_str}")  # print in engleza

                sql_where = " WHERE " + " AND ".join(conditions) if conditions else ""
                sql_history = sql_history_base + sql_where + " ORDER BY timestamp DESC"
                limit_q = limit_chart if not for_export else None
                if limit_q: sql_history += " LIMIT %s"; query_params.append(limit_q)
                cur.execute(sql_history, tuple(query_params));
                historical_data_raw = cur.fetchall()
                print(f"Fetched {len(historical_data_raw)} historical records.")  # print in engleza

                data_chart_proc = list(historical_data_raw[:limit_chart] if not for_export else historical_data_raw);
                data_chart_proc.reverse()
                for r in data_chart_proc:
                    ts, fg, vx = r.get("timestamp"), r.get("fear_greed"), r.get("vix")
                    history_timestamps.append(
                        ts.strftime('%Y-%m-%d %H:%M') if isinstance(ts, datetime.datetime) else "Invalid Date")
                    history_fg_values.append(fg if isinstance(fg, (int, float)) else None)
                    try:
                        history_vix_values.append(float(vx) if vx is not None else None)
                    except:
                        history_vix_values.append(None)
                for i, r_raw in enumerate(historical_data_raw):
                    if i >= limit_display and not for_export: break
                    r_tbl = r_raw.copy();
                    ts_tbl = r_tbl.get("timestamp")
                    r_tbl["timestamp_display"] = ts_tbl.strftime('%Y-%m-%d %H:%M') if isinstance(ts_tbl,
                                                                                                 datetime.datetime) else "N/A"
                    r_tbl["fear_greed_display"] = r_tbl.get("fear_greed", "N/A")
                    try:
                        r_tbl["vix_display"] = f"{float(r_tbl.get('vix', 0.0)):.2f}" if r_tbl.get(
                            "vix") is not None else "N/A"
                    except:
                        r_tbl["vix_display"] = "N/A"
                    history_for_table.append(r_tbl)
        except (Exception, psycopg2.DatabaseError) as error:
            print(f"Error querying database: {error}")  # print in engleza
        finally:
            if conn: conn.close(); print("Database connection closed.")  # print in engleza
    else:
        print("Could not establish DB connection.")  # print in engleza

    return {
        "latest": latest_data, "history_table": history_for_table,
        "chart_data": {"timestamps": history_timestamps, "fg_values": history_fg_values,
                       "vix_values": history_vix_values},
        "history_table_raw_for_export": historical_data_raw
    }


# --- ruta principala si pentru procesarea formularului de alerta vix ---
@app.route('/', methods=['GET', 'POST'])  # permite atat get (afisare pagina) cat si post (trimitere formular)
def index():
    """
    gestioneaza afisarea paginii principale si procesarea formularului de subscriere la alerte vix.
    """
    vix_alert_form = VixAlertSubscriptionForm()  # cream o instanta a formularului nostru

    # verificam daca request-ul este de tip post si daca datele din formular sunt valide
    if request.method == 'POST' and vix_alert_form.validate_on_submit():
        email = vix_alert_form.email.data.lower().strip()  # luam emailul, il facem litere mici si eliminam spatiile
        vix_threshold = vix_alert_form.vix_threshold.data  # luam pragul vix
        conn = None  # initializam conexiunea la db
        try:
            conn = get_db_connection()  # ne conectam la db
            if conn:
                with conn.cursor() as cur:  # deschidem un cursor
                    # verificam daca emailul exista deja in tabela de subscrieri
                    cur.execute("SELECT id FROM vix_alerts_subscriptions WHERE email = %s", (email,))
                    existing_subscription = cur.fetchone()

                    if existing_subscription:  # daca emailul exista, actualizam pragul si reactivam subscrierea
                        cur.execute("""
                            UPDATE vix_alerts_subscriptions 
                            SET vix_threshold = %s, is_active = TRUE, created_at = CURRENT_TIMESTAMP 
                            WHERE email = %s
                        """, (vix_threshold, email))
                        flash(f"Alert threshold updated for {email} to VIX > {vix_threshold}.",
                              'success')  # mesaj de succes
                    else:  # daca emailul nu exista, inseram o noua subscriere
                        cur.execute("""
                            INSERT INTO vix_alerts_subscriptions (email, vix_threshold) 
                            VALUES (%s, %s)
                        """, (email, vix_threshold))
                        flash(f"Successfully subscribed {email} for VIX alerts above {vix_threshold}.",
                              'success')  # mesaj de succes
                    conn.commit()  # salvam modificarile in db
            else:  # daca nu ne-am putut conecta la db
                flash("Database connection error. Please try again later.", 'danger')  # mesaj de eroare
        except (Exception, psycopg2.DatabaseError) as error:  # prindem erori de db sau altele
            print(f"Error processing VIX alert subscription on index page: {error}")  # print in engleza
            if conn: conn.rollback()  # anulam tranzactia daca a aparut o eroare
            flash(f"An error occurred while subscribing: {str(error)[:100]}...",
                  'danger')  # mesaj de eroare (limitam lungimea)
        finally:  # indiferent de ce se intampla
            if conn: conn.close()  # inchidem conexiunea la db
        # facem redirect la aceeasi pagina (index) pentru a curata datele din formular (pattern post/redirect/get)
        # '_anchor' face ca pagina sa sara la elementul cu id-ul respectiv
        return redirect(url_for('index', _anchor='vix-alert-subscription-card'))

        # aceasta parte se executa pentru request-urile get (cand utilizatorul doar viziteaza pagina)
    # sau daca formularul post nu a fost valid
    start_date = request.args.get('start_date')  # luam filtrele de data din url
    end_date = request.args.get('end_date')
    processed_data = get_sentiment_data_from_db(start_date_str=start_date,
                                                end_date_str=end_date)  # luam datele pentru dashboard

    # trimitem toate datele necesare catre template-ul html
    return render_template('index.html',
                           fear_greed_value=processed_data["latest"]["fear_greed_display"],
                           vix_value=processed_data["latest"]["vix_display"],
                           last_updated=processed_data["latest"]["last_updated"],
                           latest_summary=processed_data["latest"]["summary_text_display"],
                           history=processed_data.get("history_table", []),
                           chart_timestamps=json.dumps(processed_data.get("chart_data", {}).get("timestamps", [])),
                           chart_fg_values=json.dumps(processed_data.get("chart_data", {}).get("fg_values", [])),
                           chart_vix_values=json.dumps(processed_data.get("chart_data", {}).get("vix_values", [])),
                           current_start_date=start_date,
                           current_end_date=end_date,
                           vix_alert_form=vix_alert_form  # trimitem si instanta formularului la template
                           )


# ... (restul rutelor: export_csv, execute_script_on_server, run_webscrape_route, run_analyze_news_route, run_pipeline_route raman
@app.route('/export/csv')
def export_csv():
    start_date = request.args.get('start_date');
    end_date = request.args.get('end_date')
    data_dict = get_sentiment_data_from_db(for_export=True, start_date_str=start_date, end_date_str=end_date)
    history_list_raw = data_dict.get("history_table_raw_for_export", [])
    if not history_list_raw: return "No data to export for the selected criteria.", 404
    output_stream = io.StringIO();
    csv_writer = csv.writer(output_stream)
    headers = ["timestamp", "fear_greed", "vix", "summary_text"];
    csv_writer.writerow(headers)
    for record in history_list_raw:
        ts_obj = record.get("timestamp")
        ts_str = (ts_obj.strftime('%Y-%m-%d %H:%M:%S %Z') if ts_obj.tzinfo else ts_obj.strftime(
            '%Y-%m-%d %H:%M:%S UTC')) if isinstance(ts_obj, datetime.datetime) else ""
        summary = record.get("summary_text", "");
        summary_cleaned = summary.replace('\r\n', ' ').replace('\n', ' ') if summary else ""
        csv_writer.writerow([ts_str, record.get("fear_greed", ""), record.get("vix", ""), summary_cleaned])
    csv_output = output_stream.getvalue();
    output_stream.close()
    return Response(csv_output, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=sentiment_history.csv"})


def execute_script_on_server(script_path):
    try:
        print(f"Attempting to run script: {script_path} with python: {PYTHON_EXECUTABLE}")
        if not os.path.exists(PYTHON_EXECUTABLE): return {"status": "error",
                                                          "message": f"Python executable not found: {PYTHON_EXECUTABLE}"}, 500
        if not os.path.exists(script_path): return {"status": "error",
                                                    "message": f"Script not found: {script_path}"}, 500
        process = subprocess.run([PYTHON_EXECUTABLE, script_path], capture_output=True, text=True, check=False,
                                 cwd=PROJECT_ROOT, encoding='utf-8', errors='replace')
        if process.returncode == 0:
            msg = f"Script {os.path.basename(script_path)} executed successfully."
            print(msg, "\nStdout:", process.stdout)
            return {"status": "success", "message": msg, "output": process.stdout}, 200
        else:
            msg = f"Script {os.path.basename(script_path)} failed (code {process.returncode})."
            print(msg, "\nStderr:", process.stderr, "\nStdout:", process.stdout)
            return {"status": "error", "message": msg, "error_output": process.stderr, "output": process.stdout}, 500
    except Exception as e:
        msg = f"Exception running {os.path.basename(script_path)}: {str(e)}"
        print(msg)
        return {"status": "error", "message": msg}, 500


@app.route('/run_webscrape', methods=['POST'])
def run_webscrape_route():
    print("Request to run webScrape.py")
    result, status_code = execute_script_on_server(WEBSCRAPE_SCRIPT_PATH)
    return jsonify(result), status_code


@app.route('/run_analyze_news', methods=['POST'])
def run_analyze_news_route():
    print("Request to run analyze_news.py")
    result, status_code = execute_script_on_server(ANALYZE_NEWS_SCRIPT_PATH)
    return jsonify(result), status_code


@app.route('/run_pipeline', methods=['POST'])
def run_pipeline_route():
    print("Request to run full data pipeline.")
    results, overall_status = [], "success"
    result_scrape, status_scrape = execute_script_on_server(WEBSCRAPE_SCRIPT_PATH)
    results.append({"script": "webScrape.py", **result_scrape})
    if status_scrape != 200:
        overall_status = "error";
        msg = "WebScrape failed. Analyze News script skipped."
        print(msg);
        results.append({"script": "analyze_news.py", "status": "skipped", "message": msg})
        return jsonify({"status": overall_status, "pipeline_results": results}), 500
    print("WebScrape successful, proceeding to Analyze News.")
    result_analyze, status_analyze = execute_script_on_server(ANALYZE_NEWS_SCRIPT_PATH)
    results.append({"script": "analyze_news.py", **result_analyze})
    if status_analyze != 200: overall_status = "error"
    final_msg = "Data pipeline finished" + (" with errors." if overall_status == "error" else " successfully.")
    return jsonify({"status": overall_status, "message": final_msg,
                    "pipeline_results": results}), 200 if overall_status == "success" else 500


# acest bloc se executa doar cand rulezi direct 'python appflask.py'
if __name__ == '__main__':
    app.config[
        'TEMPLATES_AUTO_RELOAD'] = True  # util pentru dezvoltare, face ca flask sa reincarce template-urile html la fiecare modificare
    app.run(
        debug=True)  # porneste serverul web flask. debug=true afiseaza erori detaliate in browser si reincarca serverul la modificari in codul python.