import os
import json
import re
import psycopg2
import requests
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
AI_CONFIG_PATH = os.path.join(WEBSITE_DIR, "data_files", "ai_config.json")

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

MAX_TOKENS = 4096 # Reduced from 65536 for better compatibility with local models

def load_ai_config():
    if os.path.exists(AI_CONFIG_PATH):
        try:
            with open(AI_CONFIG_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return None

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
        return articles, vix_value
    except (FileNotFoundError, json.JSONDecodeError, Exception):
        return [], None

def parse_analysis_results(analysis_text):
    if not analysis_text:
        return {"fear_greed": None, "summary_text": "Analysis failed."}
        
    fear_greed = None
    summary_candidate = analysis_text

    # 1. Primary Regex: Look for the explicit "FEAR AND GREED INDEX = X" format
    fg_match = re.search(r"(?:FEAR AND GREED INDEX|FEAR & GREED INDEX|Fear & Greed Index|Fear and Greed Index)\s*[:=]?\s*\*?\*?(\d{1,3})\*?\*?", analysis_text, re.IGNORECASE | re.DOTALL)
    
    if fg_match:
        try:
            fear_greed = int(fg_match.group(1))
        except (ValueError, IndexError):
            pass
    
    # 2. Secondary Fallback: If no explicit index found, look for any standalone number 0-100 near the end of the text
    if fear_greed is None:
        last_lines = analysis_text.strip().split('\n')[-3:] # Check last 3 lines
        for line in last_lines:
            num_match = re.search(r"(\d{1,3})", line)
            if num_match:
                val = int(num_match.group(1))
                if 0 <= val <= 100:
                    fear_greed = val
                    break

    # 3. Final Fallback: If still None, default to a neutral 50 but keep the summary
    if fear_greed is not None:
        if not (0 <= fear_greed <= 100):
            fear_greed = 50
    else:
        # Check if the LLM mentioned specific sentiment words to guess a value
        lower_text = analysis_text.lower()
        if "extreme fear" in lower_text: fear_greed = 15
        elif "extreme greed" in lower_text: fear_greed = 85
        elif "fear" in lower_text: fear_greed = 35
        elif "greed" in lower_text: fear_greed = 65
        else: fear_greed = 50 # Default neutral

    # Clean up summary by removing <think> tags and the final index line
    summary_candidate = re.sub(r"<think>.*?</think>", "", analysis_text, flags=re.DOTALL).strip()
    summary_candidate = re.sub(r"(?:FEAR AND GREED INDEX|FEAR & GREED INDEX|Fear & Greed Index|Fear and Greed Index)\s*[:=]?\s*\*?\*?\d{1,3}\*?\*?", "", summary_candidate, flags=re.IGNORECASE).strip()
    
    return {"fear_greed": fear_greed, "summary_text": summary_candidate}

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
        }, timeout=300) # 5 minute timeout for local LLMs
        response.raise_for_status()
        return response.json().get("response")
    except Exception as e:
        print(f"Ollama Error: {e}")
        return None

def analyze_with_cloud(news_articles, config):
    p_type = config.get("provider_type", "azure").lower()
    endpoint = config.get("endpoint")
    api_key = config.get("api_key")
    model = config.get("model")
    
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
        except Exception as e:
            print(f"Azure Error: {e}")
            return None
    else:
        # Generic OpenAI compatible via requests
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
            response = requests.post(endpoint, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Cloud API Error: {e}")
            return None

def save_results_to_db(analysis_data, vix_value, timestamp):
    if not all([DB_NAME, DB_USER, DB_PASS]):
        return False
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sentiment_history (fear_greed, vix, summary_text, timestamp) VALUES (%s, %s, %s, %s)",
                (analysis_data.get("fear_greed"), vix_value, analysis_data.get("summary_text"), timestamp)
            )
            conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"DB Error: {e}")
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
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False

if __name__ == "__main__":
    articles, vix = load_data_from_json(JSON_NEWS_FILE_PATH)
    config = load_ai_config()
    
    # Default config if file doesn't exist
    if not config:
        config = {
            "provider": "ollama",
            "ollama": {"endpoint": "http://localhost:11434/api/generate", "model": "deepseek-r1:1.5b"}
        }
    
    analysis_text = None
    if articles:
        provider = config.get("provider", "ollama")
        if provider == "ollama":
            print(f"Running local analysis using Ollama ({config.get('ollama', {}).get('model')})...")
            analysis_text = analyze_with_ollama(articles, config.get("ollama", {}))
        else:
            print("Running cloud analysis...")
            analysis_text = analyze_with_cloud(articles, config.get("cloud", {}))
            
    if not analysis_text:
        print("Analysis failed to produce output. Check if Ollama is running or API keys are valid.")
            
    parsed_data = parse_analysis_results(analysis_text) if analysis_text else {"fear_greed": None, "summary_text": "Analysis skipped or failed. Ensure Ollama is running or Cloud API keys are set."}
    ts = datetime.now(timezone.utc)
    
    save_indices_to_json(parsed_data, vix, ts, INDEX_JSON_OUTPUT_PATH)
    if parsed_data.get("fear_greed") is not None:
        save_results_to_db(parsed_data, vix, ts)
