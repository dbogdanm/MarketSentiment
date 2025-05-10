from flask import Flask, render_template, Response, request, json, jsonify
import os
import datetime
from datetime import timezone
import psycopg2
from psycopg2.extras import RealDictCursor
import csv
import io
import markdown
import subprocess

app = Flask(__name__)

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

MAX_HISTORY_RECORDS_DISPLAY = 15
MAX_HISTORY_RECORDS_CHART = 50

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, ".."))

DESKTOP_PATH_GUESS = os.path.abspath(
    os.path.join(PROJECT_ROOT, "..", ".."))
PYTHON_PROJECT1_FOLDER_NAME = "PythonProject1"
VENV_FOLDER_NAME = ".venv1"

PYTHON_EXECUTABLE = os.path.join(
    DESKTOP_PATH_GUESS,
    PYTHON_PROJECT1_FOLDER_NAME,
    VENV_FOLDER_NAME,
    "Scripts",
    "python.exe"
)



WEBSCRAPE_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "website", "crucialPys", "webScrape.py")
ANALYZE_NEWS_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "website", "crucialPys", "analyze_news.py")


def get_db_connection():
    if not all([DB_NAME, DB_USER, DB_PASS]):
        print("Error: Database credentials missing.")
        return None
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        print("Successfully connected to PostgreSQL database.")
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error connecting to PostgreSQL database: {error}")
        return None


def get_sentiment_data_from_db(limit_display=MAX_HISTORY_RECORDS_DISPLAY,
                               limit_chart=MAX_HISTORY_RECORDS_CHART,
                               for_export=False,
                               start_date_str=None,
                               end_date_str=None):
    latest_data = {
        "fear_greed": 50, "vix": None, "timestamp": "N/A", "summary_text": "N/A",
        "fear_greed_display": 50, "vix_display": "N/A", "last_updated": "N/A",
        "summary_text_display": "<p>No AI summary currently available.</p>"
    }
    historical_data_raw = []
    history_for_table = []
    history_timestamps = []
    history_fg_values = []
    history_vix_values = []

    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT fear_greed, vix, summary_text, timestamp FROM sentiment_history ORDER BY timestamp DESC LIMIT 1")
                latest_row = cur.fetchone()
                if latest_row:
                    latest_data.update(latest_row)
                    print(f"Fetched latest data: {latest_row}")

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
                    latest_data["summary_text_display"] = "<p>No AI summary currently available.</p>"
                else:
                    # Presupunem că AI-ul NU returnează Markdown, deci nu mai folosim biblioteca markdown
                    # Pentru a respecta newline-urile, vom folosi <pre> sau CSS white-space: pre-wrap în HTML
                    latest_data["summary_text_display"] = raw_summary

                query_params = []
                sql_history_base = "SELECT id, fear_greed, vix, summary_text, timestamp FROM sentiment_history"
                conditions = []
                if start_date_str:
                    try:
                        start_date_obj = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').replace(hour=0,
                                                                                                        minute=0,
                                                                                                        second=0,
                                                                                                        microsecond=0,
                                                                                                        tzinfo=timezone.utc)
                        conditions.append("timestamp >= %s")
                        query_params.append(start_date_obj)
                    except ValueError:
                        print(f"Warning: Invalid start_date format: {start_date_str}")
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

                sql_where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
                sql_history_ordered = sql_history_base + sql_where_clause + " ORDER BY timestamp DESC"

                limit_for_query = limit_chart
                if for_export: limit_for_query = None

                sql_final_history = sql_history_ordered
                if limit_for_query is not None:
                    sql_final_history += " LIMIT %s"
                    query_params.append(limit_for_query)

                cur.execute(sql_final_history, tuple(query_params))
                historical_data_raw = cur.fetchall()
                print(f"Fetched {len(historical_data_raw)} historical records.")

                data_for_chart_processing = list(historical_data_raw)
                if len(data_for_chart_processing) > limit_chart and not for_export:
                    data_for_chart_processing = data_for_chart_processing[:limit_chart]
                data_for_chart_processing.reverse()

                for record in data_for_chart_processing:
                    ts, fg, vix_val = record.get("timestamp"), record.get("fear_greed"), record.get("vix")
                    history_timestamps.append(
                        ts.strftime('%Y-%m-%d %H:%M') if isinstance(ts, datetime.datetime) else "Invalid Date")
                    history_fg_values.append(fg if isinstance(fg, (int, float)) else None)
                    try:
                        history_vix_values.append(float(vix_val) if vix_val is not None else None)
                    except (ValueError, TypeError):
                        history_vix_values.append(None)

                for i, record_raw in enumerate(historical_data_raw):
                    if i >= limit_display and not for_export: break
                    record_for_table = record_raw.copy()
                    ts_table = record_for_table.get("timestamp")
                    record_for_table["timestamp_display"] = ts_table.strftime('%Y-%m-%d %H:%M') if isinstance(ts_table,
                                                                                                              datetime.datetime) else "N/A"
                    record_for_table["fear_greed_display"] = record_for_table.get("fear_greed", "N/A")
                    try:
                        record_for_table[
                            "vix_display"] = f"{float(record_for_table.get('vix', 0.0)):.2f}" if record_for_table.get(
                            "vix") is not None else "N/A"
                    except (ValueError, TypeError):
                        record_for_table["vix_display"] = "N/A"
                    history_for_table.append(record_for_table)
        except (Exception, psycopg2.DatabaseError) as error:
            print(f"Error querying database: {error}")
        finally:
            if conn: conn.close(); print("Database connection closed.")
    else:
        print("Could not establish DB connection.")

    return {
        "latest": latest_data, "history_table": history_for_table,
        "chart_data": {"timestamps": history_timestamps, "fg_values": history_fg_values,
                       "vix_values": history_vix_values},
        "history_table_raw_for_export": historical_data_raw
    }


@app.route('/')
def index():
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
                           current_end_date=end_date)


@app.route('/export/csv')
def export_csv():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    data_dict = get_sentiment_data_from_db(for_export=True, start_date_str=start_date, end_date_str=end_date)
    history_list_raw = data_dict.get("history_table_raw_for_export", [])
    if not history_list_raw: return "No data to export for the selected criteria.", 404

    output_stream = io.StringIO()
    csv_writer = csv.writer(output_stream)
    headers = ["timestamp", "fear_greed", "vix", "summary_text"]
    csv_writer.writerow(headers)
    for record in history_list_raw:
        ts_obj = record.get("timestamp")
        ts_str = (ts_obj.strftime('%Y-%m-%d %H:%M:%S %Z') if ts_obj.tzinfo else ts_obj.strftime(
            '%Y-%m-%d %H:%M:%S UTC')) if isinstance(ts_obj, datetime.datetime) else ""
        summary = record.get("summary_text", "")
        summary_cleaned = summary.replace('\r\n', ' ').replace('\n', ' ') if summary else ""
        csv_writer.writerow([ts_str, record.get("fear_greed", ""), record.get("vix", ""), summary_cleaned])
    csv_output = output_stream.getvalue()
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

        process = subprocess.run(
            [PYTHON_EXECUTABLE, script_path], capture_output=True, text=True, check=False,
            cwd=PROJECT_ROOT, encoding='utf-8', errors='replace'
        )
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
        overall_status = "error"
        msg = "WebScrape failed. Analyze News script skipped."
        print(msg)
        results.append({"script": "analyze_news.py", "status": "skipped", "message": msg})
        return jsonify({"status": overall_status, "pipeline_results": results}), 500

    print("WebScrape successful, proceeding to Analyze News.")
    result_analyze, status_analyze = execute_script_on_server(ANALYZE_NEWS_SCRIPT_PATH)
    results.append({"script": "analyze_news.py", **result_analyze})
    if status_analyze != 200: overall_status = "error"

    final_msg = "Data pipeline finished." + (" with errors." if overall_status == "error" else "")
    return jsonify({"status": overall_status, "message": final_msg,
                    "pipeline_results": results}), 200 if overall_status == "success" else 500


if __name__ == '__main__':
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True)