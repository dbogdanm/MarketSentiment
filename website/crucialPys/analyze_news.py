import os # Make sure os is imported
import json
import re
import psycopg2
from datetime import datetime, timezone

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# --- Configuration ---

# Input JSON path calculation
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.dirname(SCRIPT_DIR)
JSON_FILENAME = "financial_news_agg.json"
JSON_NEWS_FILE_PATH = os.path.join(WEBSITE_DIR, "data_files", JSON_FILENAME)

# *** NEW: Output path for the index data ***
INDEX_JSON_OUTPUT_DIR = os.path.join(WEBSITE_DIR, "data_files")
INDEX_JSON_FILENAME = "latest_indices.json" # Name for the new output file
INDEX_JSON_OUTPUT_PATH = os.path.join(INDEX_JSON_OUTPUT_DIR, INDEX_JSON_FILENAME)


print(f"Attempting to load news from: {JSON_NEWS_FILE_PATH}")
print(f"Will save latest indices to: {INDEX_JSON_OUTPUT_PATH}") # Debug output path

# Database Configuration
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

# Azure AI Configuration
AZURE_ENDPOINT_URL = "https://deepseekmds7532865580.services.ai.azure.com/models" # Verified endpoint
MODEL_NAME = "DeepSeek-R1-3" # Your specific deployment name
AZURE_API_KEY = os.environ.get("AZURE_DEEPSEEK_API_KEY")
MAX_TOKENS = 4096

# --- Functions ---

# ... (keep load_news_from_json, parse_analysis_results, analyze_news_with_deepseek functions as they are) ...
def load_news_from_json(filename):
    """Loads news articles from a JSON file, using the provided full path."""
    # No change needed inside the function itself, it already takes the path
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            news_data = json.load(f)
            print(f"Successfully loaded {len(news_data)} news articles from {filename}.")
            return news_data
    except FileNotFoundError:
        # Make the error message more informative
        print(f"Error: JSON file not found at the specified path: {filename}")
        print(f"       Current Working Directory: {os.getcwd()}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filename}. Is the file valid?")
        return None
    except Exception as e:
        print(f"An unexpected error occurred loading {filename}: {e}")
        return None

def parse_analysis_results(analysis_text):
    """Parses the AI's response to extract F&G, VIX, and the cleaned summary."""
    fear_greed = None
    vix = None
    summary = analysis_text # Default to full text if parsing fails

    # 1. Extract F&G and VIX using Regex (case-insensitive, flexible spacing)
    match = re.search(
        r"FEAR AND GREED INDEX\s*[:=]?\s*(\d{1,3}).*VIX INDEX\s*[:=]?\s*([\d.]+)",
        analysis_text,
        re.IGNORECASE | re.DOTALL
    )
    if match:
        try:
            fear_greed = int(match.group(1))
            vix = float(match.group(2))
            print(f"Parsed values - Fear&Greed: {fear_greed}, VIX: {vix}")

            # 2. Attempt to remove the <think> block if it exists BEFORE the F&G/VIX line
            # Find the end of the think block
            think_end_match = re.search(r"</think>\s*", analysis_text, re.IGNORECASE | re.DOTALL)
            if think_end_match:
                # Get text after </think> and before the F&G line
                summary_start_index = think_end_match.end()
                summary_end_index = match.start() # End summary before the FEAR AND GREED line
                summary = analysis_text[summary_start_index:summary_end_index].strip()
                # Basic cleanup of potential leading/trailing newlines that might remain
                summary = re.sub(r"^\s+", "", summary)
                summary = re.sub(r"\s+$", "", summary)
                print("Extracted summary after <think> block.")
            else:
                # If no <think> block, take text before F&G line
                 summary = analysis_text[:match.start()].strip()
                 print("Extracted summary (no <think> block found).")


        except (ValueError, IndexError) as parse_error:
            print(f"Error parsing matched values (F&G/VIX): {parse_error}. Indices will be None.")
            fear_greed = None
            vix = None
            # Attempt to clean summary even if indices failed
            think_end_match = re.search(r"</think>\s*", analysis_text, re.IGNORECASE | re.DOTALL)
            if think_end_match:
                 summary = analysis_text[think_end_match.end():].strip() # Take everything after think
                 # Remove the F&G line from the end if it's there
                 summary = re.sub(r"FEAR AND GREED INDEX.*$", "", summary, flags=re.IGNORECASE | re.DOTALL).strip()

            else:
                 summary = re.sub(r"FEAR AND GREED INDEX.*$", "", analysis_text, flags=re.IGNORECASE | re.DOTALL).strip()


    else:
        print("Warning: Could not find the specific FEAR_GREED/VIX line in the analysis output.")
        # Attempt to clean summary by removing potential think block anyway
        think_end_match = re.search(r"</think>\s*", analysis_text, re.IGNORECASE | re.DOTALL)
        if think_end_match:
             summary = analysis_text[think_end_match.end():].strip()
             print("Extracted summary after <think> block (F&G/VIX line not found).")
        else:
             summary = analysis_text # Keep original text if no think block and no F&G line
             print("Could not parse F&G/VIX, returning full text as summary.")


    return {"fear_greed": fear_greed, "vix": vix, "summary_text": summary}

def analyze_news_with_deepseek(news_articles):
    """Sends news articles to Azure DeepSeek API for analysis."""
    if not AZURE_API_KEY:
        print("Error: AZURE_DEEPSEEK_API_KEY environment variable not set.")
        return None
    if not news_articles:
        print("Error: No news articles provided for analysis.")
        return None

    # Updated system prompt: Explicitly asks *not* to include reasoning steps in the main output
    system_message_content = (
        "You are a top financial assistant, maybe the best in the world specialized in analyzing financial news regarding the US stock market. "
        "Your task is to read the provided list of news articles (in JSON format)"
        "and provide a concise summary covering the overall market sentiment (positive, negative, neutral, mixed), "
        "key events or announcements, and any recurring themes or major concerns mentioned across the articles. "
        "Base your analysis *only* on the information presented in the articles. "
        "After the summary, estimate a Fear and Greed Index value (1-100, where 1 is extreme fear, 100 is extreme greed) based *only* on the sentiment derived from the provided articles. "
        "Also, output the VIX index based on the vix_data json. "
        "IMPORTANT: Do NOT include your thought process or reasoning steps within the main response body. "
        "Conclude your entire response with a single final line containing ONLY the estimated values in the following exact format (using capital letters): "
        "\nFEAR AND GREED INDEX = [estimated F&G value] VIX INDEX = [estimated VIX value]"
    )
    # Format user message with the news articles
    try:
        news_json_string = json.dumps(news_articles, indent=2)
    except TypeError as e:
        print(f"Error encoding news articles to JSON: {e}")
        return None

    user_message_content = f" You are top financial analyst, please analyze the following news articles and provide the summary and index values as instructed.\n\nNews Articles:\n{news_json_string}\n\nAnalysis Summary and Index Values:\n"

    try:
        # Initialize Azure Client
        client = ChatCompletionsClient(
            endpoint=AZURE_ENDPOINT_URL,
            credential=AzureKeyCredential(AZURE_API_KEY),
        )
    except Exception as e:
        print(f"Error initializing Azure ChatCompletionsClient: {e}")
        return None

    messages = [
        SystemMessage(content=system_message_content),
        UserMessage(content=user_message_content),
    ]

    print("\n--- Calling Azure DeepSeek API ---")
    try:
        # Make the API Call
        response = client.complete(
            messages=messages,
            model=MODEL_NAME, # Or your specific deployment name if different
            max_tokens=MAX_TOKENS,
            temperature=0.5 # Adjust temperature for desired creativity/factuality
        )
        print("--- API Call Successful ---")

        # Process the response
        if response.choices and len(response.choices) > 0:
             message = response.choices[0].message
             if message and hasattr(message, 'content'):
                 return message.content
             else:
                 print("Error: API response structure unexpected (no content). Full response:", response)
                 return None
        else:
            print("Error: Received an empty or invalid response from API. Full response:", response)
            return None

    except HttpResponseError as e:
        print(f"Error during Azure API call: Status Code {e.status_code}, Reason: {e.reason}")
        # Optionally print more details if available: print(e.error)
        return None
    except Exception as e:
        print(f"An unexpected error occurred during the API call: {e}")
        return None

def save_results_to_db(parsed_data, timestamp):
    """Saves the parsed analysis results to the PostgreSQL database."""
    if not all([DB_NAME, DB_USER, DB_PASS]):
        print("Error: Database credentials (DB_NAME, DB_USER, DB_PASS) not set.")
        return False
    if not parsed_data or parsed_data.get("summary_text") is None:
         print("Error: No valid parsed data provided to save to DB.")
         return False

    conn = None; inserted = False
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        print(f"Connected to PostgreSQL database '{DB_NAME}' on '{DB_HOST}'.")
        with conn.cursor() as cur:
            sql = """
            INSERT INTO sentiment_history (fear_greed, vix, summary_text, timestamp)
            VALUES (%s, %s, %s, %s) RETURNING id;
            """
            cur.execute(sql, (
                parsed_data.get("fear_greed"),
                parsed_data.get("vix"),
                parsed_data.get("summary_text"),
                timestamp # Use the provided timestamp
            ))
            inserted_id = cur.fetchone()
            conn.commit()
            if inserted_id: print(f"Successfully inserted DB record with ID: {inserted_id[0]}.")
            else: print("Successfully inserted DB record (no ID returned).")
            inserted = True
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error writing to PostgreSQL database: {error}")
        if conn: conn.rollback()
    finally:
        if conn is not None: conn.close(); print("Database connection closed.")
    return inserted

# *** NEW FUNCTION to save indices to JSON ***
def save_indices_to_json(parsed_data, timestamp, output_path):
    """Saves the F&G, VIX, and timestamp to a JSON file."""
    if not parsed_data:
        print("Error: Cannot save indices to JSON, no parsed data provided.")
        return False

    # Prepare data dictionary
    index_data = {
        "fear_greed": parsed_data.get("fear_greed"), # Will be null if parsing failed
        "vix": parsed_data.get("vix"),             # Will be null if parsing failed
        "timestamp_utc": timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp) # Ensure ISO format string
    }

    try:
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        # Write the JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2)
        print(f"Successfully saved latest indices to {output_path}")
        return True
    except IOError as e:
        print(f"Error saving indices JSON to {output_path}: {e}")
        return False
    except TypeError as e:
        print(f"Error serializing index data to JSON: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred saving indices JSON: {e}")
        return False


# --- Main Execution ---

if __name__ == "__main__":
    print("Starting news analysis process...")
    articles = load_news_from_json(JSON_NEWS_FILE_PATH)
    analysis_result_text = None
    parsed_data = None

    if articles:
        analysis_result_text = analyze_news_with_deepseek(articles)

        if analysis_result_text:
            print("\n--- Raw Analysis Result from API ---")
            print(analysis_result_text)
            print("------------------------------------")
            parsed_data = parse_analysis_results(analysis_result_text)

            if not parsed_data or parsed_data.get("summary_text") is None or not parsed_data.get("summary_text").strip():
                 print("Error: Parsing resulted in empty or invalid summary. Cannot process further.")
                 parsed_data = None
            elif parsed_data.get("fear_greed") is None or parsed_data.get("vix") is None:
                 print("Warning: Could not parse Fear&Greed or VIX index. Indices file/DB record will have null values.")

        else:
            print("\nAnalysis failed or returned no text. Cannot parse or save.")

    else:
        print("Could not load news data. Cannot perform analysis.")

    # Proceed only if parsing was initiated and potentially successful (even with null indices)
    if parsed_data:
        print("\n--- Parsed Data ---")
        print(f"  Fear & Greed: {parsed_data.get('fear_greed')}")
        print(f"  VIX: {parsed_data.get('vix')}")
        print(f"  Summary: {parsed_data.get('summary_text')[:200]}...")
        print("-------------------")

        # Define the timestamp ONCE for both outputs
        current_analysis_timestamp = datetime.now(timezone.utc)

        # Save indices to JSON file
        save_indices_to_json(parsed_data, current_analysis_timestamp, INDEX_JSON_OUTPUT_PATH)

        # Save full results to database
        save_results_to_db(parsed_data, current_analysis_timestamp)

    else:
        print("No valid parsed data available to save to JSON file or database.")

    print("\nAnalysis process finished.")