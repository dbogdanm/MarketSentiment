"""Sends aggregated news to an LLM (local Ollama or a cloud provider),
parses the resulting market-sentiment summary and Fear & Greed index, and
persists the results to PostgreSQL plus a JSON cache for the dashboard."""

import json
import logging
import os
import re
from datetime import datetime, timezone

import psycopg2
import requests
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("analyze_news")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.dirname(SCRIPT_DIR)
JSON_FILENAME = "financial_news_agg.json"
JSON_NEWS_FILE_PATH = os.path.join(WEBSITE_DIR, "data_files", JSON_FILENAME)
INDEX_JSON_OUTPUT_DIR = os.path.join(WEBSITE_DIR, "data_files")
INDEX_JSON_FILENAME = "latest_indices.json"
INDEX_JSON_OUTPUT_PATH = os.path.join(INDEX_JSON_OUTPUT_DIR, INDEX_JSON_FILENAME)
AI_CONFIG_PATH = os.path.join(WEBSITE_DIR, "data_files", "ai_config.json")

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
DB_CONNECT_TIMEOUT = int(os.environ.get("DB_CONNECT_TIMEOUT", "5"))

MAX_TOKENS = 4096  # Kept small for compatibility with local models.
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "300"))
CLOUD_TIMEOUT = int(os.environ.get("CLOUD_TIMEOUT", "60"))

# Matches the "FEAR AND GREED INDEX = 75" marker the prompt asks the model
# to emit, tolerating "&"/"and", optional colon/equals and markdown bold.
FG_MARKER = r"FEAR\s*(?:AND|&)\s*GREED\s*INDEX"


def load_ai_config():
    if os.path.exists(AI_CONFIG_PATH):
        try:
            with open(AI_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError) as error:
            logger.warning("Could not read AI config %s: %s", AI_CONFIG_PATH, error)
    return None


def load_data_from_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            full_data = json.load(f)
    except (OSError, ValueError) as error:
        logger.warning("Could not load news data from %s: %s", filename, error)
        return [], None

    articles = full_data.get("articles", [])
    vix_value = None
    vix_value_raw = full_data.get("vix_data", {}).get("vix")
    if vix_value_raw is not None:
        try:
            vix_value = float(vix_value_raw)
        except (ValueError, TypeError):
            vix_value = None
    return articles, vix_value


def parse_analysis_results(analysis_text):
    """Extract the Fear & Greed score and a cleaned summary from raw LLM
    output. Returns fear_greed=None when no plausible score is found so the
    caller can decide not to persist unreliable data."""
    if not analysis_text:
        return {"fear_greed": None, "summary_text": ""}

    fear_greed = None

    # 1. Primary: the explicit "FEAR AND GREED INDEX = X" marker.
    fg_match = re.search(rf"{FG_MARKER}\s*[:=]?\s*\*{{0,2}}(\d{{1,3}})\*{{0,2}}", analysis_text, re.IGNORECASE)
    if fg_match:
        val = int(fg_match.group(1))
        if 0 <= val <= 100:
            fear_greed = val

    # 2. Fallback: a standalone 0-100 number near the end of the text.
    if fear_greed is None:
        last_lines = analysis_text.strip().split('\n')[-3:]
        for line in last_lines:
            if re.search(FG_MARKER, line, re.IGNORECASE):
                continue
            num_match = re.search(r"\b(\d{1,3})\b", line)
            if num_match:
                val = int(num_match.group(1))
                if 0 <= val <= 100:
                    fear_greed = val
                    break

    # Clean the summary: drop <think> reasoning blocks and the index marker
    # line (even a malformed one without a numeric value).
    summary = re.sub(r"<think>.*?</think>", "", analysis_text, flags=re.DOTALL).strip()
    summary = re.sub(rf"[ \t]*{FG_MARKER}[ \t]*[:=]?[ \t]*\*{{0,2}}\w*\*{{0,2}}[ \t]*\n?", "", summary, flags=re.IGNORECASE).strip()

    # 3. Last resort: infer a score from sentiment wording in the summary.
    if fear_greed is None:
        lower_text = summary.lower()
        if "extreme fear" in lower_text:
            fear_greed = 15
        elif "extreme greed" in lower_text:
            fear_greed = 85
        elif "fear" in lower_text:
            fear_greed = 35
        elif "greed" in lower_text:
            fear_greed = 65

    return {"fear_greed": fear_greed, "summary_text": summary}


def analyze_with_ollama(news_articles, config):
    endpoint = config.get("endpoint", "http://localhost:11434/api/generate")
    model = config.get("model", "deepseek-r1:1.5b")

    prompt = (
        "Instructions: Analyze the following financial news articles. "
        "Provide a concise summary of the overall market sentiment. "
        "You MAY use markdown (bolding, lists) to improve readability. "
        "At the very end of your response, you MUST provide a numeric Fear & Greed Index score between 0 and 100 "
        "where 0 is extreme fear and 100 is extreme greed. "
        "Format the final line exactly like this: FEAR AND GREED INDEX = [value]\n\n"
        f"Articles: {json.dumps(news_articles)}"
    )

    try:
        response = requests.post(endpoint, json={
            "model": model,
            "prompt": prompt,
            "stream": False
        }, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        return response.json().get("response")
    except requests.exceptions.RequestException as error:
        logger.error("Ollama request failed: %s", error)
        return None
    except ValueError as error:
        logger.error("Ollama returned invalid JSON: %s", error)
        return None


def analyze_with_cloud(news_articles, config):
    p_type = config.get("provider_type", "azure").lower()
    endpoint = config.get("endpoint")
    api_key = config.get("api_key")
    model = config.get("model")

    if not endpoint or not api_key:
        logger.error("Cloud provider selected but endpoint/api_key are not configured.")
        return None

    system_msg = "You are a financial analyst. Analyze news and conclude with 'FEAR AND GREED INDEX = [value]'. You may use markdown."
    user_msg = f"Articles: {json.dumps(news_articles)}"

    if p_type == "azure":
        try:
            client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))
            response = client.complete(
                messages=[SystemMessage(content=system_msg), UserMessage(content=user_msg)],
                model=model,
                max_tokens=MAX_TOKENS,
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception as error:
            logger.error("Azure AI request failed: %s", error)
            return None

    # Generic OpenAI-compatible endpoint.
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            "max_tokens": MAX_TOKENS
        }
        response = requests.post(endpoint, headers=headers, json=data, timeout=CLOUD_TIMEOUT)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except (requests.exceptions.RequestException, KeyError, ValueError) as error:
        logger.error("Cloud API request failed: %s", error)
        return None


def save_results_to_db(analysis_data, vix_value, timestamp):
    # Re-read credentials at call time so values loaded after import
    # (e.g. dotenv in a parent process or test fixtures) are picked up.
    db_host = os.environ.get("DB_HOST", DB_HOST or "localhost")
    db_name = os.environ.get("DB_NAME", DB_NAME)
    db_user = os.environ.get("DB_USER", DB_USER)
    db_pass = os.environ.get("DB_PASS", DB_PASS)

    if not all([db_name, db_user, db_pass]):
        logger.warning("Database credentials not configured; skipping DB save.")
        return False
    try:
        conn = psycopg2.connect(
            host=db_host, database=db_name, user=db_user, password=db_pass,
            connect_timeout=DB_CONNECT_TIMEOUT,
        )
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sentiment_history (fear_greed, vix, summary_text, timestamp) VALUES (%s, %s, %s, %s)",
                (analysis_data.get("fear_greed"), vix_value, analysis_data.get("summary_text"), timestamp)
            )
            conn.commit()
        conn.close()
        logger.info("Saved analysis results to database.")
        return True
    except psycopg2.Error as error:
        logger.error("Failed to save analysis results to database: %s", error)
        return False


def save_indices_to_json(analysis_data, vix_value, timestamp, output_path):
    data = {
        "fear_greed": analysis_data.get("fear_greed"),
        "vix": vix_value,
        "summary_text": analysis_data.get("summary_text"),
        "timestamp_utc": timestamp.isoformat()
    }
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except OSError as error:
        logger.error("Failed to write %s: %s", output_path, error)
        return False


def main():
    articles, vix = load_data_from_json(JSON_NEWS_FILE_PATH)
    config = load_ai_config()

    if not config:
        config = {
            "provider": "ollama",
            "ollama": {"endpoint": "http://localhost:11434/api/generate", "model": "deepseek-r1:1.5b"}
        }

    analysis_text = None
    if articles:
        provider = config.get("provider", "ollama")
        if provider == "ollama":
            logger.info("Running local analysis using Ollama (%s)...", config.get('ollama', {}).get('model'))
            analysis_text = analyze_with_ollama(articles, config.get("ollama", {}))
        else:
            logger.info("Running cloud analysis...")
            analysis_text = analyze_with_cloud(articles, config.get("cloud", {}))
    else:
        logger.warning("No articles found in %s; run the scraper first.", JSON_NEWS_FILE_PATH)

    if analysis_text:
        parsed_data = parse_analysis_results(analysis_text)
    else:
        logger.error("Analysis produced no output. Check that Ollama is running or cloud API keys are valid.")
        parsed_data = {"fear_greed": None, "summary_text": "Analysis skipped or failed. Ensure Ollama is running or Cloud API keys are set."}

    ts = datetime.now(timezone.utc)

    save_indices_to_json(parsed_data, vix, ts, INDEX_JSON_OUTPUT_PATH)
    if parsed_data.get("fear_greed") is not None:
        save_results_to_db(parsed_data, vix, ts)
    else:
        logger.warning("No Fear & Greed score parsed; skipping database save to avoid storing unreliable data.")


if __name__ == "__main__":
    main()
