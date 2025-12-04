import os
import json
import re
import psycopg2
from datetime import datetime, timezone
import smtplib
from email.mime.text import MIMEText
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.dirname(SCRIPT_DIR)
JSON_FILENAME = "financial_news_agg.json"
JSON_NEWS_FILE_PATH = os.path.join(WEBSITE_DIR, "data_files", JSON_FILENAME)
INDEX_JSON_OUTPUT_DIR = os.path.join(WEBSITE_DIR, "data_files")
INDEX_JSON_FILENAME = "latest_indices.json"
INDEX_JSON_OUTPUT_PATH = os.path.join(INDEX_JSON_OUTPUT_DIR, INDEX_JSON_FILENAME)

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = os.environ.get("SMTP_PORT")
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")
VIX_ALERT_THRESHOLD = os.environ.get("VIX_ALERT_THRESHOLD")

AZURE_ENDPOINT_URL = "https://deepseekmds7532865580.services.ai.azure.com/models"
MODEL_NAME = "DeepSeek-R1-3"
AZURE_API_KEY = os.environ.get("AZURE_DEEPSEEK_API_KEY")
MAX_TOKENS = 65536

def load_data_from_json(filename):
    articles = []
    vix_value = None
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            full_data = json.load(f)

        articles = full_data.get("articles", [])
        vix_data = full_data.get("vix_data", {})
        vix_value_raw = vix_data.get("vix")

        if vix_value_raw is not None:
            try:
                vix_value = float(vix_value_raw)
            except (ValueError, TypeError):
                vix_value = None
        else:
            vix_value = None
            
        return articles, vix_value

    except (FileNotFoundError, json.JSONDecodeError, Exception):
        return [], None

def parse_analysis_results(analysis_text):
    fear_greed = None
    summary_candidate = analysis_text

    fg_match = re.search(r"FEAR AND GREED INDEX\s*[:=]?\s*(\d{1,3})", analysis_text, re.IGNORECASE | re.DOTALL)

    if fg_match:
        try:
            fear_greed_value_str = fg_match.group(1)
            fear_greed = int(fear_greed_value_str)
            if not (0 <= fear_greed <= 100):
                fear_greed = None
        except (ValueError, IndexError):
            fear_greed = None

        part_before_fg = analysis_text[:fg_match.start()].rstrip()
        part_after_fg = analysis_text[fg_match.end():].lstrip()

        if part_before_fg and part_after_fg:
            summary_candidate = part_before_fg + "\n" + part_after_fg
        elif part_before_fg:
            summary_candidate = part_before_fg
        elif part_after_fg:
            summary_candidate = part_after_fg
        else:
            summary_candidate = ""
    else:
        summary_candidate = re.sub(r"FEAR AND GREED INDEX.*$", "", summary_candidate, count=1, flags=re.IGNORECASE | re.DOTALL).strip()

    final_summary = summary_candidate
    think_end_match = re.search(r"</think>\s*", final_summary, re.IGNORECASE | re.DOTALL)

    if think_end_match:
        final_summary = final_summary[think_end_match.end():].strip()
    else:
        final_summary = final_summary.strip()

    return {"fear_greed": fear_greed, "summary_text": final_summary}

def analyze_news_with_deepseek(news_articles):
    if not AZURE_API_KEY:
        return None
    if not news_articles:
        return None

    system_message_content = (
        "You are a top financial assistant specialized in analyzing financial news regarding the US stock market. "
        "Your task is to read the provided list of news articles (in JSON format) "
        "and provide a long complex answer covering the overall market sentiment (positive, negative, neutral, mixed), "
        "key events or announcements, and any recurring themes or major concerns mentioned across the articles. "
        "Base your analysis *only* on the information presented in the articles. "
        "Once again, DON'T USE MARKDOWN."
        "IMPORTANT: Do include your thought process or reasoning steps within the main response body and DON'T answer using Markdown."
        "When you change the sentence's topic, leave some room before talking about the next topic but don't insert any spaces before the first sentence."
        "Write a long-long answer, use as many tokens as possible."
        "Conclude your entire response with a single final line containing ONLY the estimated Fear and Greed value in the following exact format (using capital letters): "
        "\nFEAR AND GREED INDEX = [estimated F&G value]"
    )
    
    try:
        news_json_string = json.dumps(news_articles, indent=2)
    except TypeError:
        return None

    user_message_content = f"You are top financial analyst, please analyze the following news articles and provide the summary and the Fear & Greed index value as instructed.\n\nNews Articles:\n{news_json_string}\n\nAnalysis Summary and Index Value:\n"

    try:
        client = ChatCompletionsClient(endpoint=AZURE_ENDPOINT_URL, credential=AzureKeyCredential(AZURE_API_KEY))
    except Exception:
        return None

    messages = [
        SystemMessage(content=system_message_content),
        UserMessage(content=user_message_content),
    ]

    try:
        response = client.complete(
            messages=messages,
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS,
            temperature=0.5
        )
        
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return response.choices[0].message.content
        else:
            return None
    except (HttpResponseError, Exception):
        return None

def save_results_to_db(analysis_data, vix_value, timestamp):
    if not all([DB_NAME, DB_USER, DB_PASS]):
        return False
    if not analysis_data or analysis_data.get("summary_text") is None:
        return False

    conn = None
    inserted = False
    
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        with conn.cursor() as cur:
            sql = """INSERT INTO sentiment_history (fear_greed, vix, summary_text, timestamp) VALUES (%s, %s, %s, %s) RETURNING id;"""
            cur.execute(sql, (
                analysis_data.get("fear_greed"),
                vix_value,
                analysis_data.get("summary_text"),
                timestamp
            ))
            conn.commit()
            inserted = True
    except (Exception, psycopg2.DatabaseError):
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            
    return inserted

def save_indices_to_json(fg_value, vix_value, timestamp, output_path):
    index_data = {
        "fear_greed": fg_value, 
        "vix": vix_value,
        "timestamp_utc": timestamp.isoformat(timespec='seconds') + 'Z'
    }

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2)
        return True
    except Exception:
        return False

if __name__ == "__main__":
    analysis_result_text = None
    parsed_analysis_data = None
    actual_vix_value = None

    if os.path.exists(JSON_NEWS_FILE_PATH):
        articles, actual_vix_value = load_data_from_json(JSON_NEWS_FILE_PATH)

        if articles:
            analysis_result_text = analyze_news_with_deepseek(articles)
            if analysis_result_text:
                parsed_analysis_data = parse_analysis_results(analysis_result_text)

                if not parsed_analysis_data or not parsed_analysis_data.get("summary_text", "").strip():
                    parsed_analysis_data = None
                elif parsed_analysis_data.get("fear_greed") is None:
                    pass

    if parsed_analysis_data or actual_vix_value is not None:
        data_for_saving = parsed_analysis_data if parsed_analysis_data else {"fear_greed": None, "summary_text": "News analysis failed or skipped."}

        current_analysis_timestamp = datetime.now(timezone.utc)

        save_indices_to_json(
            data_for_saving.get("fear_greed"),
            actual_vix_value,
            current_analysis_timestamp,
            INDEX_JSON_OUTPUT_PATH
        )

        if parsed_analysis_data:
            save_results_to_db(
                data_for_saving,
                actual_vix_value,
                current_analysis_timestamp
            )
