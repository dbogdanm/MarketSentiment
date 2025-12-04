import os
import datetime
from datetime import timezone
import psycopg2
from psycopg2.extras import RealDictCursor
import csv
import io
import subprocess

from flask import Flask, render_template, Response, request, json, jsonify, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField
from wtforms.validators import DataRequired, Email, NumberRange

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'o_cheie_secreta_foarte_puternica_si_aleatorie_123!')

class VixAlertSubscriptionForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(message="Email is required."), Email(message="Invalid email address.")])
    vix_threshold = FloatField('VIX Threshold', validators=[DataRequired(message="VIX threshold is required."), NumberRange(min=0, message="Threshold must be a non-negative number.")])
    submit = SubmitField('Subscribe / Update Alert')

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

MAX_HISTORY_RECORDS_DISPLAY = 15
MAX_HISTORY_RECORDS_CHART = 50

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, ".."))
DESKTOP_PATH_GUESS = os.path.abspath(os.path.join(PROJECT_ROOT, "..", ".."))
PYTHON_PROJECT1_FOLDER_NAME = "PythonProject1"
VENV_FOLDER_NAME = ".venv1"
PYTHON_EXECUTABLE = os.path.join(DESKTOP_PATH_GUESS, PYTHON_PROJECT1_FOLDER_NAME, VENV_FOLDER_NAME, "Scripts", "python.exe")
WEBSCRAPE_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "website", "crucialPys", "webScrape.py")
ANALYZE_NEWS_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "website", "crucialPys", "analyze_news.py")

def get_db_connection():
    if not all([DB_NAME, DB_USER, DB_PASS]):
        return None
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        return conn
    except (Exception, psycopg2.DatabaseError):
        return None

def get_sentiment_data_from_db(limit_display=MAX_HISTORY_RECORDS_DISPLAY, limit_chart=MAX_HISTORY_RECORDS_CHART, for_export=False, start_date_str=None, end_date_str=None):
    latest_data = {
        "fear_greed": 50, "vix": None, "timestamp": "N/A", "summary_text": "N/A",
        "fear_greed_display": 50, "vix_display": "N/A", "last_updated": "N/A",
        "summary_text_display": "No AI summary currently available."
    }
    historical_data_raw, history_for_table, history_timestamps, history_fg_values, history_vix_values = [], [], [], [], []

    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT fear_greed, vix, summary_text, timestamp FROM sentiment_history ORDER BY timestamp DESC LIMIT 1")
                latest_row = cur.fetchone()
                if latest_row:
                    latest_data.update(latest_row)

                if latest_data.get("fear_greed") is None or not isinstance(latest_data.get("fear_greed"), (int, float)) or not (0 <= latest_data.get("fear_greed", 50) <= 100):
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
                    latest_data["last_updated"] = ts_latest.strftime('%Y-%m-%d %H:%M:%S %Z') if ts_latest.tzinfo else ts_latest.strftime('%Y-%m-%d %H:%M:%S UTC')
                elif isinstance(ts_latest, str) and ts_latest != "N/A":
                    latest_data["last_updated"] = ts_latest
                else:
                    latest_data["last_updated"] = "N/A"

                raw_summary = latest_data.get("summary_text")
                if not raw_summary or raw_summary.strip() == "N/A":
                    latest_data["summary_text_display"] = "No AI summary currently available."
                else:
                    latest_data["summary_text_display"] = raw_summary

                query_params, conditions = [], []
                sql_history_base = "SELECT id, fear_greed, vix, summary_text, timestamp FROM sentiment_history"
                if start_date_str:
                    try:
                        start_date_obj = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
                        conditions.append("timestamp >= %s")
                        query_params.append(start_date_obj)
                    except ValueError:
                        pass
                if end_date_str:
                    try:
                        end_date_obj = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
                        conditions.append("timestamp <= %s")
                        query_params.append(end_date_obj)
                    except ValueError:
                        pass

                sql_where = " WHERE " + " AND ".join(conditions) if conditions else ""
                sql_history = sql_history_base + sql_where + " ORDER BY timestamp DESC"
                limit_q = limit_chart if not for_export else None
                if limit_q:
                    sql_history += " LIMIT %s"
                    query_params.append(limit_q)
                cur.execute(sql_history, tuple(query_params))
                historical_data_raw = cur.fetchall()

                data_chart_proc = list(historical_data_raw[:limit_chart] if not for_export else historical_data_raw)
                data_chart_proc.reverse()
                for r in data_chart_proc:
                    ts, fg, vx = r.get("timestamp"), r.get("fear_greed"), r.get("vix")
                    history_timestamps.append(ts.strftime('%Y-%m-%d %H:%M') if isinstance(ts, datetime.datetime) else "Invalid Date")
                    history_fg_values.append(fg if isinstance(fg, (int, float)) else None)
                    try:
                        history_vix_values.append(float(vx) if vx is not None else None)
                    except:
                        history_vix_values.append(None)
                for i, r_raw in enumerate(historical_data_raw):
                    if i >= limit_display and not for_export:
                        break
                    r_tbl = r_raw.copy()
                    ts_tbl = r_tbl.get("timestamp")
                    r_tbl["timestamp_display"] = ts_tbl.strftime('%Y-%m-%d %H:%M') if isinstance(ts_tbl, datetime.datetime) else "N/A"
                    r_tbl["fear_greed_display"] = r_tbl.get("fear_greed", "N/A")
                    try:
                        r_tbl["vix_display"] = f"{float(r_tbl.get('vix', 0.0)):.2f}" if r_tbl.get("vix") is not None else "N/A"
                    except:
                        r_tbl["vix_display"] = "N/A"
                    history_for_table.append(r_tbl)
        except (Exception, psycopg2.DatabaseError):
            pass
        finally:
            if conn:
                conn.close()

    return {
        "latest": latest_data,
        "history_table": history_for_table,
        "chart_data": {"timestamps": history_timestamps, "fg_values": history_fg_values, "vix_values": history_vix_values},
        "history_table_raw_for_export": historical_data_raw
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    vix_alert_form = VixAlertSubscriptionForm()

    if request.method == 'POST' and vix_alert_form.validate_on_submit():
        email = vix_alert_form.email.data.lower().strip()
        vix_threshold = vix_alert_form.vix_threshold.data
        conn = None
        try:
            conn = get_db_connection()
            if conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM vix_alerts_subscriptions WHERE email = %s", (email,))
                    existing_subscription = cur.fetchone()

                    if existing_subscription:
                        cur.execute("""
                            UPDATE vix_alerts_subscriptions 
                            SET vix_threshold = %s, is_active = TRUE, created_at = CURRENT_TIMESTAMP 
                            WHERE email = %s
                        """, (vix_threshold, email))
                        flash(f"Alert threshold updated for {email} to VIX > {vix_threshold}.", 'success')
                    else:
                        cur.execute("""
                            INSERT INTO vix_alerts_subscriptions (email, vix_threshold) 
                            VALUES (%s, %s)
                        """, (email, vix_threshold))
                        flash(f"Successfully subscribed {email} for VIX alerts above {vix_threshold}.", 'success')
                    conn.commit()
            else:
                flash("Database connection error. Please try again later.", 'danger')
        except (Exception, psycopg2.DatabaseError) as error:
            if conn:
                conn.rollback()
            flash(f"An error occurred while subscribing: {str(error)[:100]}...", 'danger')
        finally:
            if conn:
                conn.close()
        return redirect(url_for('index', _anchor='vix-alert-subscription-card'))

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    processed_data = get_sentiment_data_from_db(start_date_str=start_date, end_date_str=end_date)

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
                           vix_alert_form=vix_alert_form
                           )

@app.route('/export/csv')
def export_csv():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    data_dict = get_sentiment_data_from_db(for_export=True, start_date_str=start_date, end_date_str=end_date)
    history_list_raw = data_dict.get("history_table_raw_for_export", [])
    
    if not history_list_raw:
        return "No data to export for the selected criteria.", 404
        
    output_stream = io.StringIO()
    csv_writer = csv.writer(output_stream)
    headers = ["timestamp", "fear_greed", "vix", "summary_text"]
    csv_writer.writerow(headers)
    
    for record in history_list_raw:
        ts_obj = record.get("timestamp")
        ts_str = (ts_obj.strftime('%Y-%m-%d %H:%M:%S %Z') if ts_obj.tzinfo else ts_obj.strftime('%Y-%m-%d %H:%M:%S UTC')) if isinstance(ts_obj, datetime.datetime) else ""
        summary = record.get("summary_text", "")
        summary_cleaned = summary.replace('\r\n', ' ').replace('\n', ' ') if summary else ""
        csv_writer.writerow([ts_str, record.get("fear_greed", ""), record.get("vix", ""), summary_cleaned])
        
    csv_output = output_stream.getvalue()
    output_stream.close()
    
    return Response(csv_output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=sentiment_history.csv"})

def execute_script_on_server(script_path):
    try:
        if not os.path.exists(PYTHON_EXECUTABLE):
            return {"status": "error", "message": f"Python executable not found: {PYTHON_EXECUTABLE}"}, 500
        if not os.path.exists(script_path):
            return {"status": "error", "message": f"Script not found: {script_path}"}, 500
            
        process = subprocess.run([PYTHON_EXECUTABLE, script_path], capture_output=True, text=True, check=False, cwd=PROJECT_ROOT, encoding='utf-8', errors='replace')
        
        if process.returncode == 0:
            return {"status": "success", "message": f"Script {os.path.basename(script_path)} executed successfully.", "output": process.stdout}, 200
        else:
            return {"status": "error", "message": f"Script {os.path.basename(script_path)} failed (code {process.returncode}).", "error_output": process.stderr, "output": process.stdout}, 500
    except Exception as e:
        return {"status": "error", "message": f"Exception running {os.path.basename(script_path)}: {str(e)}"}, 500

@app.route('/run_webscrape', methods=['POST'])
def run_webscrape_route():
    result, status_code = execute_script_on_server(WEBSCRAPE_SCRIPT_PATH)
    return jsonify(result), status_code

@app.route('/run_analyze_news', methods=['POST'])
def run_analyze_news_route():
    result, status_code = execute_script_on_server(ANALYZE_NEWS_SCRIPT_PATH)
    return jsonify(result), status_code

@app.route('/run_pipeline', methods=['POST'])
def run_pipeline_route():
    results = []
    overall_status = "success"
    
    result_scrape, status_scrape = execute_script_on_server(WEBSCRAPE_SCRIPT_PATH)
    results.append({"script": "webScrape.py", **result_scrape})
    
    if status_scrape != 200:
        overall_status = "error"
        results.append({"script": "analyze_news.py", "status": "skipped", "message": "WebScrape failed. Analyze News script skipped."})
        return jsonify({"status": overall_status, "pipeline_results": results}), 500
        
    result_analyze, status_analyze = execute_script_on_server(ANALYZE_NEWS_SCRIPT_PATH)
    results.append({"script": "analyze_news.py", **result_analyze})
    
    if status_analyze != 200:
        overall_status = "error"
        
    final_msg = "Data pipeline finished" + (" with errors." if overall_status == "error" else " successfully.")
    return jsonify({"status": overall_status, "message": final_msg, "pipeline_results": results}), 200 if overall_status == "success" else 500

if __name__ == '__main__':
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True)
