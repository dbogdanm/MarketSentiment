import csv
import datetime
import io
import json
import logging
import os
import secrets
import subprocess
import sys
import threading
from datetime import timezone

import psycopg2
from dotenv import load_dotenv
from flask import Flask, Response, flash, jsonify, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from psycopg2.extras import RealDictCursor
from wtforms import FloatField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, NumberRange

load_dotenv()

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
logger = logging.getLogger("appFlask")

app = Flask(__name__)

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    logger.warning(
        "FLASK_SECRET_KEY is not set; generated an ephemeral key. "
        "Sessions and CSRF tokens will not survive restarts or scale across workers. "
        "Set FLASK_SECRET_KEY in production."
    )
app.config["SECRET_KEY"] = SECRET_KEY


class VixAlertSubscriptionForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(message="Email is required."), Email(message="Invalid email address.")])
    vix_threshold = FloatField('VIX Threshold', validators=[DataRequired(message="VIX threshold is required."), NumberRange(min=0, message="Threshold must be a non-negative number.")])
    submit = SubmitField('Subscribe / Update Alert')


class SettingsForm(FlaskForm):
    provider = StringField('Active Provider', validators=[DataRequired()])
    ollama_endpoint = StringField('Ollama Endpoint')
    ollama_model = StringField('Ollama Model')
    cloud_provider_type = StringField('Cloud Provider Type')
    cloud_endpoint = StringField('Cloud Endpoint')
    cloud_api_key = StringField('Cloud API Key')
    cloud_model = StringField('Cloud Model')
    submit_settings = SubmitField('Save Settings')


DB_HOST = os.environ.get("DB_HOST", "db")
DB_NAME = os.environ.get("DB_NAME", "marketsentiment")
DB_USER = os.environ.get("DB_USER", "user")
DB_PASS = os.environ.get("DB_PASS", "password")
DB_CONNECT_TIMEOUT = int(os.environ.get("DB_CONNECT_TIMEOUT", "5"))

MAX_HISTORY_RECORDS_DISPLAY = 15
MAX_HISTORY_RECORDS_CHART = 50
SCRIPT_TIMEOUT_SECONDS = int(os.environ.get("SCRIPT_TIMEOUT_SECONDS", "900"))

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, ".."))
PYTHON_EXECUTABLE = sys.executable
WEBSCRAPE_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "website", "crucialPys", "webScrape.py")
ANALYZE_NEWS_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "website", "crucialPys", "analyze_news.py")
LATEST_JSON_PATH = os.path.join(PROJECT_ROOT, "website", "data_files", "latest_indices.json")
AI_CONFIG_PATH = os.path.join(PROJECT_ROOT, "website", "data_files", "ai_config.json")

# Prevents concurrent pipeline runs triggered from the dashboard buttons.
_script_lock = threading.Lock()


def get_db_connection():
    if not all([DB_NAME, DB_USER, DB_PASS]):
        logger.warning("Database credentials are not fully configured.")
        return None
    try:
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            connect_timeout=DB_CONNECT_TIMEOUT,
        )
    except psycopg2.Error as error:
        logger.error("Database connection failed: %s", error)
        return None


def get_sentiment_data_from_db(limit_display=MAX_HISTORY_RECORDS_DISPLAY, limit_chart=MAX_HISTORY_RECORDS_CHART, for_export=False, start_date_str=None, end_date_str=None):
    latest_data = {
        "fear_greed": 50, "vix": None, "timestamp": "N/A", "summary_text": "N/A",
        "fear_greed_display": 50, "vix_display": "N/A", "last_updated": "N/A",
        "summary_text_display": "No AI summary currently available."
    }

    # Fallback to the JSON cache so the dashboard still shows the latest
    # pipeline output when the database is unreachable.
    if os.path.exists(LATEST_JSON_PATH):
        try:
            with open(LATEST_JSON_PATH, 'r', encoding='utf-8') as f:
                j_data = json.load(f)
            latest_data["fear_greed_display"] = j_data.get("fear_greed", 50)
            latest_data["vix_display"] = f"{float(j_data.get('vix', 0)):.2f}" if j_data.get("vix") else "N/A"
            latest_data["last_updated"] = j_data.get("timestamp_utc", "N/A")
            latest_data["summary_text_display"] = j_data.get("summary_text") or "No AI summary currently available."
        except (OSError, ValueError) as error:
            logger.warning("Could not read JSON cache %s: %s", LATEST_JSON_PATH, error)

    historical_data_raw, history_for_table, history_timestamps, history_fg_values, history_vix_values = [], [], [], [], []

    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT fear_greed, vix, summary_text, timestamp FROM sentiment_history ORDER BY timestamp DESC LIMIT 1")
                latest_row = cur.fetchone()
                if latest_row:
                    latest_data.update(latest_row)

                fg = latest_data.get("fear_greed")
                if isinstance(fg, (int, float)) and 0 <= fg <= 100:
                    latest_data["fear_greed_display"] = fg
                else:
                    latest_data["fear_greed_display"] = 50

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
                        logger.warning("Ignoring invalid start_date filter: %r", start_date_str)
                if end_date_str:
                    try:
                        end_date_obj = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
                        conditions.append("timestamp <= %s")
                        query_params.append(end_date_obj)
                    except ValueError:
                        logger.warning("Ignoring invalid end_date filter: %r", end_date_str)

                sql_where = " WHERE " + " AND ".join(conditions) if conditions else ""
                sql_history = sql_history_base + sql_where + " ORDER BY timestamp DESC"
                if not for_export:
                    sql_history += " LIMIT %s"
                    query_params.append(limit_chart)
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
                    except (ValueError, TypeError):
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
                    except (ValueError, TypeError):
                        r_tbl["vix_display"] = "N/A"
                    history_for_table.append(r_tbl)
        except psycopg2.Error as error:
            logger.error("Failed to read sentiment history: %s", error)
        finally:
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
        except psycopg2.Error as error:
            if conn:
                conn.rollback()
            logger.error("VIX alert subscription failed: %s", error)
            flash("An error occurred while subscribing. Please try again later.", 'danger')
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


@app.route('/healthz')
def healthz():
    conn = get_db_connection()
    db_status = "up" if conn else "down"
    if conn:
        conn.close()
    return jsonify({"status": "ok", "database": db_status}), 200


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
    script_name = os.path.basename(script_path)
    logger.info("Executing %s with %s", script_path, PYTHON_EXECUTABLE)
    try:
        if not os.path.exists(script_path):
            logger.error("Script not found: %s", script_path)
            return {"status": "error", "message": f"Script not found: {script_path}"}, 500

        process = subprocess.run(
            [PYTHON_EXECUTABLE, script_path],
            capture_output=True, text=True, check=False, cwd=PROJECT_ROOT,
            encoding='utf-8', errors='replace', timeout=SCRIPT_TIMEOUT_SECONDS,
        )

        if process.returncode == 0:
            logger.info("%s executed successfully", script_name)
            return {"status": "success", "message": f"Script {script_name} executed successfully.", "output": process.stdout}, 200

        logger.error("%s failed (exit code %s): %s", script_name, process.returncode, process.stderr)
        return {"status": "error", "message": f"Script {script_name} failed.", "error_output": process.stderr, "output": process.stdout}, 500
    except subprocess.TimeoutExpired:
        logger.error("%s timed out after %s seconds", script_name, SCRIPT_TIMEOUT_SECONDS)
        return {"status": "error", "message": f"Script {script_name} timed out after {SCRIPT_TIMEOUT_SECONDS} seconds."}, 500
    except Exception as e:
        logger.exception("Exception while running %s", script_name)
        return {"status": "error", "message": f"Exception running {script_name}: {e}"}, 500


def _busy_response():
    return jsonify({"status": "error", "message": "Another script run is already in progress. Please try again shortly."}), 409


@app.route('/run_webscrape', methods=['POST'])
def run_webscrape_route():
    if not _script_lock.acquire(blocking=False):
        return _busy_response()
    try:
        result, status_code = execute_script_on_server(WEBSCRAPE_SCRIPT_PATH)
    finally:
        _script_lock.release()
    return jsonify(result), status_code


@app.route('/run_analyze_news', methods=['POST'])
def run_analyze_news_route():
    if not _script_lock.acquire(blocking=False):
        return _busy_response()
    try:
        result, status_code = execute_script_on_server(ANALYZE_NEWS_SCRIPT_PATH)
    finally:
        _script_lock.release()
    return jsonify(result), status_code


@app.route('/run_pipeline', methods=['POST'])
def run_pipeline_route():
    if not _script_lock.acquire(blocking=False):
        return _busy_response()
    try:
        results = []
        overall_status = "success"

        result_scrape, status_scrape = execute_script_on_server(WEBSCRAPE_SCRIPT_PATH)
        results.append({"script": "webScrape.py", **result_scrape})

        if status_scrape != 200:
            results.append({"script": "analyze_news.py", "status": "skipped", "message": "WebScrape failed. Analyze News script skipped."})
            return jsonify({"status": "error", "pipeline_results": results}), 500

        result_analyze, status_analyze = execute_script_on_server(ANALYZE_NEWS_SCRIPT_PATH)
        results.append({"script": "analyze_news.py", **result_analyze})

        if status_analyze != 200:
            overall_status = "error"

        final_msg = "Data pipeline finished" + (" with errors." if overall_status == "error" else " successfully.")
        return jsonify({"status": overall_status, "message": final_msg, "pipeline_results": results}), 200 if overall_status == "success" else 500
    finally:
        _script_lock.release()


def load_ai_config():
    try:
        if os.path.exists(AI_CONFIG_PATH):
            with open(AI_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (OSError, ValueError) as error:
        logger.warning("Could not load AI config %s: %s", AI_CONFIG_PATH, error)
    return {
        "provider": "ollama",
        "ollama": {
            "endpoint": "http://localhost:11434/api/generate",
            "model": "deepseek-r1:1.5b"
        },
        "cloud": {
            "provider_type": "azure",
            "endpoint": "",
            "api_key": "",
            "model": ""
        }
    }


def save_ai_config(config):
    os.makedirs(os.path.dirname(AI_CONFIG_PATH), exist_ok=True)
    with open(AI_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    form = SettingsForm()
    config = load_ai_config()

    if request.method == 'POST' and form.validate_on_submit():
        config['provider'] = request.form.get('provider', 'ollama')
        config['ollama']['endpoint'] = form.ollama_endpoint.data
        config['ollama']['model'] = form.ollama_model.data
        config['cloud']['provider_type'] = form.cloud_provider_type.data
        config['cloud']['endpoint'] = form.cloud_endpoint.data

        # Only update API key if user provided one, otherwise keep existing
        if form.cloud_api_key.data and form.cloud_api_key.data.strip():
            config['cloud']['api_key'] = form.cloud_api_key.data.strip()

        config['cloud']['model'] = form.cloud_model.data

        save_ai_config(config)
        flash("AI Settings saved successfully.", "success")
        return redirect(url_for('settings'))

    if request.method == 'GET':
        form.provider.data = config.get('provider', 'ollama')
        form.ollama_endpoint.data = config.get('ollama', {}).get('endpoint', '')
        form.ollama_model.data = config.get('ollama', {}).get('model', '')
        form.cloud_provider_type.data = config.get('cloud', {}).get('provider_type', 'azure')
        form.cloud_endpoint.data = config.get('cloud', {}).get('endpoint', '')
        form.cloud_api_key.data = ""  # Do not send API key back to form for security
        form.cloud_model.data = config.get('cloud', {}).get('model', '')

    return render_template('settings.html', form=form, config=config)


def init_db():
    logger.info("Initializing database schema...")
    conn = get_db_connection()
    if not conn:
        logger.warning("Could not connect to database for initialization; skipping.")
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sentiment_history (
                    id SERIAL PRIMARY KEY,
                    fear_greed INTEGER,
                    vix NUMERIC,
                    summary_text TEXT,
                    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vix_alerts_subscriptions (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    vix_threshold NUMERIC NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    last_alert_sent_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Upgrade path for databases created before the alert cooldown column existed.
            cur.execute("ALTER TABLE vix_alerts_subscriptions ADD COLUMN IF NOT EXISTS last_alert_sent_at TIMESTAMPTZ;")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_history_timestamp ON sentiment_history (timestamp DESC);")
            conn.commit()
        logger.info("Database schema initialized successfully.")
        return True
    except psycopg2.Error as error:
        logger.error("Error initializing database: %s", error)
        return False
    finally:
        conn.close()


# Gunicorn imports this module directly (it never runs the __main__ block),
# so schema initialization has to happen at import time. CREATE TABLE IF NOT
# EXISTS is idempotent, making this safe across multiple workers. Set
# AUTO_INIT_DB=0 to skip (e.g. in tests or when migrations are managed
# externally).
if os.environ.get("AUTO_INIT_DB", "1") == "1":
    init_db()


if __name__ == '__main__':
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", host=os.environ.get("FLASK_RUN_HOST", "127.0.0.1"))
