import os
import json
import re
import psycopg2
from datetime import datetime, timezone

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
print(f"Attempting to load data from: {JSON_NEWS_FILE_PATH}")
print(f"Will save latest indices to: {INDEX_JSON_OUTPUT_PATH}")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
AZURE_ENDPOINT_URL = "https://deepseekmds7532865580.services.ai.azure.com/models"
MODEL_NAME = "DeepSeek-R1-3"
AZURE_API_KEY = os.environ.get("AZURE_DEEPSEEK_API_KEY")

if not AZURE_API_KEY:
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("!!! CRITICAL WARNING: AZURE_DEEPSEEK_API_KEY not found in environment variables!")
    print("!!! Azure AI API call will fail.")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

MAX_TOKENS = 4096

def load_data_from_json(filename):
    """Loads news articles and VIX data from the combined JSON file."""
    articles = []
    vix_value = None
    print(f"--- Inside load_data_from_json for {filename} ---")
    try:
        with open(filename, 'r', encoding='utf-8') as f: full_data = json.load(f)

        articles = full_data.get("articles", [])
        print(f"Successfully loaded {len(articles)} news articles key from {filename}.")
        vix_data = full_data.get("vix_data", {})
        vix_value_raw = vix_data.get("vix")
        if vix_value_raw is not None:
            try: vix_value = float(vix_value_raw); print(f"Loaded VIX value ({vix_value}) from {filename}.")
            except (ValueError, TypeError): print(f"Warn: Invalid VIX value in {filename}: '{vix_value_raw}'."); vix_value = None
        else: print(f"Warn: 'vix' key missing/null in {filename}."); vix_value = None
        return articles, vix_value
    except FileNotFoundError: print(f"Error: Combined JSON not found: {filename}"); return [], None
    except json.JSONDecodeError as e: print(f"Error: Could not decode JSON: {filename}. Error: {e}"); return [], None
    except Exception as e: print(f"Unexpected error loading {filename}: {e}"); return [], None

def parse_analysis_results(analysis_text):
    """
    Parses the raw text output from the AI model to extract
    the Fear & Greed index and a summary.
    It attempts to remove the "FEAR AND GREED INDEX" line from the summary.

    Args:
        analysis_text (str): The text response from the AI.

    Returns:
        dict: A dictionary containing "fear_greed" (int or None)
              and "summary_text" (str).
    """
    fear_greed = None

    summary_candidate = analysis_text

    fg_match = re.search(r"FEAR AND GREED INDEX\s*[:=]?\s*(\d{1,3})", analysis_text, re.IGNORECASE | re.DOTALL)

    if fg_match:
        try:
            fear_greed_value_str = fg_match.group(1)
            fear_greed = int(fear_greed_value_str)
            if not (0 <= fear_greed <= 100):
                print(f"Warn: Parsed F&G value {fear_greed} is out of 0-100 range. Setting to None.")
                fear_greed = None
            else:
                print(f"Parsed value - Fear&Greed: {fear_greed}")
        except (ValueError, IndexError) as parse_error:
            print(f"Error parsing F&G value from '{fg_match.group(0)}': {parse_error}. F&G=None.")
            fear_greed = None

        summary_candidate = analysis_text[:fg_match.start()].rstrip() + analysis_text[fg_match.end():].lstrip()

    else:

        print("Warn: FEAR AND GREED INDEX line with numeric value not found. F&G=None.")

        summary_candidate = re.sub(r"FEAR AND GREED INDEX.*$", "", summary_candidate, count=1, flags=re.IGNORECASE | re.DOTALL).strip()

    final_summary = summary_candidate
    think_end_match = re.search(r"</think>\s*", final_summary, re.IGNORECASE | re.DOTALL)

    if think_end_match:
        final_summary = final_summary[think_end_match.end():].strip()
        print("Extracted summary after <think> block.")
    else:

        final_summary = final_summary.strip()
        print("Extracted summary (no <think> block found or summary was already clean).")

    return {"fear_greed": fear_greed, "summary_text": final_summary}

def analyze_news_with_deepseek(news_articles):

    if not AZURE_API_KEY: print("Error: AZURE_DEEPSEEK_API_KEY env var not set."); return None
    if not news_articles: print("Error: No news articles provided."); return None
    system_message_content = ("...")
    system_message_content = (
        "You are a top financial assistant specialized in analyzing financial news regarding the US stock market. "
        "Your task is to read the provided list of news articles (in JSON format) "
        "and provide a concise summary covering the overall market sentiment (positive, negative, neutral, mixed), "
        "key events or announcements, and any recurring themes or major concerns mentioned across the articles. "
        "Base your analysis *only* on the information presented in the articles. "
        "IMPORTANT: Do NOT include your thought process or reasoning steps within the main response body. "
        "Conclude your entire response with a single final line containing ONLY the estimated Fear and Greed value in the following exact format (using capital letters): "
        "\nFEAR AND GREED INDEX = [estimated F&G value]"
    )
    try: news_json_string = json.dumps(news_articles, indent=2)
    except TypeError as e: print(f"Error encoding news to JSON: {e}"); return None
    user_message_content = f"You are top financial analyst, please analyze the following news articles and provide the summary and the Fear & Greed index value as instructed.\n\nNews Articles:\n{news_json_string}\n\nAnalysis Summary and Index Value:\n"
    try: client = ChatCompletionsClient(endpoint=AZURE_ENDPOINT_URL, credential=AzureKeyCredential(AZURE_API_KEY))
    except Exception as e: print(f"Error initializing Azure Client: {e}"); return None
    messages = [ SystemMessage(content=system_message_content), UserMessage(content=user_message_content), ]
    print("\n--- Calling Azure DeepSeek API ---")
    try:
        response = client.complete( messages=messages, model=MODEL_NAME, max_tokens=MAX_TOKENS, temperature=0.5 )
        print("--- API Call Successful ---")
        if response.choices and response.choices[0].message and response.choices[0].message.content: return response.choices[0].message.content
        else: print("Error: API response unexpected.", response); return None
    except HttpResponseError as e: print(f"Error during Azure API call: Status {e.status_code}, Reason: {e.reason}"); return None
    except Exception as e: print(f"Unexpected error during API call: {e}"); return None

def save_results_to_db(analysis_data, vix_value, timestamp):

    if not all([DB_NAME, DB_USER, DB_PASS]): print("Error: DB credentials missing."); return False
    if not analysis_data or analysis_data.get("summary_text") is None: print("Error: No valid analysis data for DB."); return False
    conn = None; inserted = False
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        print(f"Connected to PostgreSQL DB '{DB_NAME}'.")
        with conn.cursor() as cur:
            sql = """INSERT INTO sentiment_history (fear_greed, vix, summary_text, timestamp) VALUES (%s, %s, %s, %s) RETURNING id;"""
            cur.execute(sql, ( analysis_data.get("fear_greed"), vix_value, analysis_data.get("summary_text"), timestamp ))
            inserted_id = cur.fetchone(); conn.commit()
            if inserted_id: print(f"Successfully inserted DB record ID: {inserted_id[0]}.")
            else: print("Successfully inserted DB record (no ID returned).")
            inserted = True
    except (Exception, psycopg2.DatabaseError) as error: print(f"Error writing to PostgreSQL DB: {error}"); conn and conn.rollback()
    finally: conn and conn.close(); print("Database connection closed.")
    return inserted

def save_indices_to_json(fg_value, vix_value, timestamp, output_path):

    index_data = { "fear_greed": fg_value, "vix": vix_value, "timestamp_utc": timestamp.isoformat(timespec='seconds') + 'Z' }

    print(f"--- Data being saved to {output_path} ---")
    print(json.dumps(index_data, indent=2))
    print("----------------------------------------")

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f: json.dump(index_data, f, indent=2)
        print(f"Successfully saved latest indices to {output_path}")
        return True
    except Exception as e: print(f"An error occurred saving indices JSON to {output_path}: {e}"); return False

if __name__ == "__main__":
    print("Starting news analysis process...")
    analysis_result_text = None
    parsed_analysis_data = None
    actual_vix_value = None

    if not os.path.exists(JSON_NEWS_FILE_PATH):
        print(f"CRITICAL ERROR: Input file {JSON_NEWS_FILE_PATH} does not exist. Run webScrape.py first.")
    else:
        print(f"Input file {JSON_NEWS_FILE_PATH} found. Proceeding with loading.")
        articles, actual_vix_value = load_data_from_json(JSON_NEWS_FILE_PATH)

        print(f"*** DEBUG: Loaded articles count = {len(articles) if articles else 0} ***")
        print(f"*** DEBUG: Loaded actual_vix_value = {actual_vix_value} ***")

        if articles:
            analysis_result_text = analyze_news_with_deepseek(articles)
            if analysis_result_text:
                print("\n--- Raw Analysis Result from API ---"); print(analysis_result_text); print("------------------------------------")
                parsed_analysis_data = parse_analysis_results(analysis_result_text)

                print(f"*** DEBUG: Parsed analysis data = {parsed_analysis_data} ***")

                if not parsed_analysis_data or not parsed_analysis_data.get("summary_text", "").strip():
                     print("Error: Parsing resulted in empty/invalid summary. Cannot save."); parsed_analysis_data = None
                elif parsed_analysis_data.get("fear_greed") is None: print("Warn: Could not parse F&G index.")
            else: print("\nAnalysis failed or returned no text.")
        else: print("Could not load news articles. Cannot perform analysis.")

    print(f"\n*** DEBUG: Check before saving: parsed_analysis_data is {'truthy' if parsed_analysis_data else 'falsy'}, actual_vix_value is {'not None' if actual_vix_value is not None else 'None'} ***")

    if parsed_analysis_data or actual_vix_value is not None:
        data_for_saving = parsed_analysis_data if parsed_analysis_data else {"fear_greed": None, "summary_text": "News analysis failed or skipped."}
        print("\n--- Final Data (Ready to Save) ---")
        print(f"  Fear & Greed: {data_for_saving.get('fear_greed')}")
        print(f"  VIX: {actual_vix_value}")
        print(f"  Summary: {data_for_saving.get('summary_text', '')[:200]}...")
        print("-------------------")
        current_analysis_timestamp = datetime.now(timezone.utc)

        json_save_success = save_indices_to_json( data_for_saving.get("fear_greed"), actual_vix_value, current_analysis_timestamp, INDEX_JSON_OUTPUT_PATH )

        print(f"*** DEBUG: save_indices_to_json returned: {json_save_success} ***")

        if parsed_analysis_data:
            db_save_success = save_results_to_db( data_for_saving, actual_vix_value, current_analysis_timestamp )

            print(f"*** DEBUG: save_results_to_db returned: {db_save_success} ***")

        else: print("Skipping database save.")
    else:
        print("No valid analysis data or VIX value available to save.")

    print("\nAnalysis process finished.")