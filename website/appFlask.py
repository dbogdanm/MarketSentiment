from flask import Flask, render_template
import os
import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import json

app = Flask(__name__)
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

MAX_HISTORY_RECORDS = 50

def get_db_connection():

    if not all([DB_NAME, DB_USER, DB_PASS]):
        print("Error: Database credentials missing in environment variables.")
        return None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error connecting to PostgreSQL database: {error}")
        return None

def get_sentiment_data_from_db():
    latest_data = { "fear_greed": 50, "vix": None, "timestamp": "N/A" }
    historical_data_raw = []
    conn = get_db_connection()

    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                cur.execute("SELECT fear_greed, vix, timestamp FROM sentiment_history ORDER BY timestamp DESC LIMIT 1")
                latest_row = cur.fetchone()
                if latest_row:
                    latest_data = latest_row
                    print(f"Fetched latest data: {latest_row}")

                cur.execute(f"SELECT fear_greed, vix, timestamp FROM sentiment_history ORDER BY timestamp DESC LIMIT {MAX_HISTORY_RECORDS}")
                historical_data_raw = cur.fetchall()
                print(f"Fetched {len(historical_data_raw)} historical records.")

        except (Exception, psycopg2.DatabaseError) as error:
            print(f"Error querying database: {error}")
        finally:
            conn.close()
    else:
        print("Could not establish database connection.")

    if latest_data.get("fear_greed") is None or not isinstance(latest_data.get("fear_greed"), (int, float)) or not (0 <= latest_data["fear_greed"] <= 100):
        latest_data["fear_greed_display"] = 50
    else:
        latest_data["fear_greed_display"] = latest_data["fear_greed"]

    if latest_data.get("vix") is None:
        latest_data["vix_display"] = "N/A"
    else:
        try: latest_data["vix_display"] = f"{float(latest_data['vix']):.2f}"
        except (ValueError, TypeError): latest_data["vix_display"] = "N/A"

    if isinstance(latest_data.get("timestamp"), datetime.datetime):

        if latest_data["timestamp"].tzinfo:
            latest_data["last_updated"] = latest_data["timestamp"].strftime('%Y-%m-%d %H:%M:%S %Z')
        else:
             latest_data["last_updated"] = latest_data["timestamp"].strftime('%Y-%m-%d %H:%M:%S')
    else:
        latest_data["last_updated"] = "N/A"

    historical_data_raw.reverse()

    history_for_table = []
    history_timestamps = []
    history_fg_values = []
    history_vix_values = []

    for record in historical_data_raw:

        ts = record.get("timestamp")
        fg = record.get("fear_greed")
        vix = record.get("vix")

        if isinstance(ts, datetime.datetime):
            history_timestamps.append(ts.strftime('%Y-%m-%d %H:%M'))
        else:
             history_timestamps.append("Invalid Date")

        history_fg_values.append(fg if isinstance(fg, (int, float)) else None)
        try:
            history_vix_values.append(float(vix) if vix is not None else None)
        except (ValueError, TypeError):
             history_vix_values.append(None)

        record_for_table = record.copy()
        if isinstance(record_for_table.get("timestamp"), datetime.datetime):
            record_for_table["timestamp_display"] = record_for_table["timestamp"].strftime('%Y-%m-%d %H:%M')
        else:
            record_for_table["timestamp_display"] = "N/A"

        record_for_table["fear_greed_display"] = record_for_table.get("fear_greed", "N/A")
        try:
            record_for_table["vix_display"] = f"{float(record_for_table['vix']):.2f}" if record_for_table.get("vix") is not None else "N/A"
        except (ValueError, TypeError):
             record_for_table["vix_display"] = "N/A"
        history_for_table.append(record_for_table)

    history_for_table.reverse()

    return {
        "latest": latest_data,
        "history_table": history_for_table,
        "chart_data": {
             "timestamps": history_timestamps,
             "fg_values": history_fg_values,
             "vix_values": history_vix_values
        }
    }

@app.route('/')
def index():
    processed_data = get_sentiment_data_from_db()

    fear_greed_display_value = processed_data["latest"].get("fear_greed_display", 50)
    vix_display_value = processed_data["latest"].get("vix_display", "N/A")
    last_updated_display = processed_data["latest"].get("last_updated", "N/A")

    return render_template('index.html',
                           fear_greed_value=fear_greed_display_value,
                           vix_value=vix_display_value,
                           last_updated=last_updated_display,
                           history=processed_data.get("history_table", []),

                           chart_timestamps=json.dumps(processed_data.get("chart_data", {}).get("timestamps", [])),
                           chart_fg_values=json.dumps(processed_data.get("chart_data", {}).get("fg_values", [])),
                           chart_vix_values=json.dumps(processed_data.get("chart_data", {}).get("vix_values", []))
                           )

if __name__ == '__main__':
    app.run(debug=True)