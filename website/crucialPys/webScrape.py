# webScrape.py

import json
import time
from datetime import datetime, timezone, timedelta
import os
import html
import re
import sys

# --- Optional Library Imports ---
try: import feedparser; FEEDPARSER_AVAILABLE = True
except ImportError: print("Warn: feedparser not found."); FEEDPARSER_AVAILABLE = False; feedparser = None
try: from newsapi import NewsApiClient, NewsAPIException; NEWSAPI_AVAILABLE = True
except ImportError: print("Warn: newsapi-python not found."); NEWSAPI_AVAILABLE = False; NewsApiClient, NewsAPIException = None, None
try: import yfinance as yf; YFINANCE_AVAILABLE = True
except ImportError: print("Warn: yfinance not found."); YFINANCE_AVAILABLE = False; yf = None
try: from bs4 import BeautifulSoup; BS4_AVAILABLE = True
except ImportError: print("Warn: beautifulsoup4 not found."); BS4_AVAILABLE = False; BeautifulSoup = None
try: import requests; REQUESTS_AVAILABLE = True
except ImportError: print("Warn: requests not found."); REQUESTS_AVAILABLE = False; requests = None

# --- Configuration ---
NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY')
NEWSAPI_QUERY = '(finance OR stock market OR economy OR investing OR earnings OR fed OR rates) AND (market OR stocks OR business)'
NEWSAPI_SOURCES = 'bloomberg,reuters,the-wall-street-journal,financial-post,cnbc,business-insider,fortune,associated-press'
NEWSAPI_LANGUAGE = 'en'
NEWSAPI_SORT_BY = 'publishedAt'
NEWSAPI_PAGE_SIZE = 50
NEWSAPI_MAX_PAGES = 3

RSS_FEEDS_GENERAL = [
    ('Google News (Reuters Site)', 'https://news.google.com/rss/search?q=site%3Areuters.com+when%3A1d&hl=en-US&gl=US&ceid=US%3Aen'),
    ('Yahoo Finance Market News', 'https://finance.yahoo.com/news/rssindex'),
]
RSS_FEEDS_MARKETS = [
     ('Investing.com News', 'https://www.investing.com/rss/news.rss'),
     ('MarketWatch Top Stories', 'https://feeds.marketwatch.com/marketwatch/topstories/'),
     ('CNBC Top News', 'https://www.cnbc.com/id/100003114/device/rss/rss.html'),
     ('Seeking Alpha Market Currents', 'https://seekingalpha.com/market_currents.xml'),
]
ALL_RSS_FEEDS = RSS_FEEDS_GENERAL + RSS_FEEDS_MARKETS
MAX_ARTICLES_PER_FEED = 20

YAHOO_TICKERS = [ '^GSPC', '^IXIC', '^DJI', '^VIX', 'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'JPM', 'BAC', 'XOM', 'CVX', 'WMT', 'COST' ]
MAX_ARTICLES_PER_TICKER = 5 # Note: .news is unreliable

MAX_TOTAL_ARTICLES = 250
OUTPUT_FILENAME = "financial_news_agg.json"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(WEBSITE_DIR, "data_files")

MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 15
REQUEST_DELAY_SOURCES = 0.5
RSS_FETCH_DELAY_FEEDS = 0.2

# --- Helper Functions ---
def clean_html_summary(summary_html):
    if not summary_html or not isinstance(summary_html, str): return "N/A"
    summary_text = summary_html
    if BS4_AVAILABLE and '<' in summary_text and '>' in summary_text:
        try: soup = BeautifulSoup(summary_html, "html.parser"); summary_text = ' '.join(soup.stripped_strings)
        except Exception as e: print(f"  Warn: BS4 parse failed: {e}. Falling back."); summary_text = re.sub('<[^<]+?>', ' ', summary_html); summary_text = ' '.join(summary_text.split())
    elif '<' in summary_text and '>' in summary_text: summary_text = re.sub('<[^<]+?>', ' ', summary_html); summary_text = ' '.join(summary_text.split())
    return html.unescape(summary_text).strip()

def format_timestamp_from_parsed(parsed_time):
    if not parsed_time: return None
    try: dt_naive = datetime.fromtimestamp(time.mktime(parsed_time)); dt_utc = dt_naive.replace(tzinfo=timezone.utc); return dt_utc.isoformat(timespec='seconds') + 'Z'
    except (ValueError, TypeError, OverflowError) as e: print(f"  Warn: Could not format from struct_time {parsed_time}: {e}"); return None

def format_timestamp(date_input):
    if not date_input: return None
    if isinstance(date_input, (int, float)):
        try:
            if date_input > 1e11: date_input /= 1000.0
            dt = datetime.fromtimestamp(float(date_input), tz=timezone.utc); return dt.isoformat(timespec='seconds') + 'Z'
        except (ValueError, OSError) as e: print(f"  Warn: Could not parse numeric ts '{date_input}': {e}"); return None
    if isinstance(date_input, str):
        date_str = date_input.strip()
        if sys.version_info >= (3, 7): formats_to_try = ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z', '%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S']
        else: formats_to_try = ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S']
        for fmt in formats_to_try:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None: dt = dt.replace(tzinfo=timezone.utc)
                else: dt = dt.astimezone(timezone.utc)
                return dt.isoformat(timespec='seconds') + 'Z'
            except (ValueError, TypeError): continue
        if date_str.isdigit():
             try: ts_val = int(date_str); dt = datetime.fromtimestamp(ts_val / 1000.0 if ts_val > 1e11 else ts_val, tz=timezone.utc); return dt.isoformat(timespec='seconds') + 'Z'
             except (ValueError, OSError): pass
        print(f"  Warn: Could not parse string ts format: '{date_input}'")
        return None
    if isinstance(date_input, time.struct_time): return format_timestamp_from_parsed(date_input)
    print(f"  Warn: Unhandled ts type: {type(date_input)} value: {date_input}"); return None

def fetch_url_with_retry(url, headers=None):
    if not REQUESTS_AVAILABLE: print("  ERROR: 'requests' needed."); return None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT); response.raise_for_status(); return response.content
        except requests.exceptions.RequestException as e:
            print(f"  Attempt {attempt+1}/{MAX_RETRIES}: Error fetch {url}: {e}")
            if isinstance(e, requests.exceptions.HTTPError) and 400 <= e.response.status_code < 500: print(f"  Client error {e.response.status_code}, stopping retry."); break
        if attempt < MAX_RETRIES - 1: time.sleep(RETRY_DELAY)
    print(f"  ERROR: Failed fetch {url} after {MAX_RETRIES} attempts."); return None

# --- Data Fetching Functions ---
def get_rss_news():
    # ...(Keep existing get_rss_news function)...
    if not FEEDPARSER_AVAILABLE or not REQUESTS_AVAILABLE: return []
    print("\n--- Fetching news from RSS Feeds ---")
    all_news = []; processed_links = set()
    for source_name, url in ALL_RSS_FEEDS:
        print(f"Fetching feed: {source_name} ({url})")
        headers = {'User-Agent': 'Mozilla/5.0'}
        rss_content = fetch_url_with_retry(url, headers)
        if not rss_content: continue
        try:
            feed = feedparser.parse(rss_content)
            if feed.bozo: print(f"  Warn: Feed '{source_name}' ill-formed: {feed.bozo_exception}")
            if not feed.entries: print(f"  Info: Feed '{source_name}' empty."); continue
            count = 0
            for entry in feed.entries:
                if count >= MAX_ARTICLES_PER_FEED: break
                link = entry.get('link')
                if link and link not in processed_links:
                    processed_links.add(link)
                    timestamp_raw = entry.get('published_parsed') or entry.get('updated_parsed') or entry.get('published') or entry.get('updated')
                    timestamp = format_timestamp(timestamp_raw)
                    summary_raw = entry.get('description', entry.get('summary', 'N/A'))
                    summary = clean_html_summary(summary_raw)
                    title = clean_html_summary(entry.get('title', 'N/A'))
                    if not title or title == 'N/A': continue
                    title = re.sub(r'\s+-\s+[^-]+$', '', title).strip() if source_name.startswith('Google News') else title
                    publisher = entry.get('source', {}).get('title')
                    source_display_name = f"Google News ({publisher})" if source_name.startswith('Google News') and publisher else f"RSS ({source_name})"
                    formatted_item = {'title': title, 'url': link, 'summary': summary, 'timestamp': timestamp, 'source_name': source_display_name}
                    all_news.append(formatted_item); count += 1
            print(f"  Fetched {count} valid items from {source_name}.")
        except Exception as e: print(f"  ERROR parsing feed '{source_name}': {e}")
        time.sleep(RSS_FETCH_DELAY_FEEDS)
    print(f"--- Finished RSS fetching. Found {len(all_news)} items. ---")
    return all_news

def get_newsapi_news():
    # ...(Keep existing get_newsapi_news function)...
    if not NEWSAPI_AVAILABLE: return []
    if not NEWSAPI_KEY: print("Error: NEWSAPI_KEY env var not set."); return []
    print("\n--- Fetching news from NewsAPI.org ---")
    all_news = []; processed_links = set()
    newsapi = NewsApiClient(api_key=NEWSAPI_KEY)
    from_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
    for page_num in range(1, NEWSAPI_MAX_PAGES + 1):
        print(f"  Fetching page {page_num}/{NEWSAPI_MAX_PAGES}...")
        response = None; success = False
        for attempt in range(MAX_RETRIES):
            try:
                response = newsapi.get_everything(q=NEWSAPI_QUERY, sources=NEWSAPI_SOURCES, language=NEWSAPI_LANGUAGE, sort_by=NEWSAPI_SORT_BY, page_size=NEWSAPI_PAGE_SIZE, page=page_num, from_param=from_date)
                success = True; break
            except NewsAPIException as e:
                print(f"  Attempt {attempt+1}/{MAX_RETRIES}: NewsAPI error (Page {page_num}): {e}")
                if e.get_code() in ['rateLimited', 'maximumResultsReached']: print(f"  {e.get_code()}, stopping NewsAPI fetch."); page_num = NEWSAPI_MAX_PAGES; break
                if attempt < MAX_RETRIES - 1: time.sleep(RETRY_DELAY * (attempt + 1))
            except Exception as e: print(f"  Attempt {attempt+1}/{MAX_RETRIES}: Unexpected NewsAPI error: {e}"); time.sleep(RETRY_DELAY * (attempt + 1))
        if not success or response is None or response.get('status') != 'ok': print(f"  Failed NewsAPI page {page_num}. Status: {response.get('status') if response else 'N/A'}"); break
        articles = response.get('articles', [])
        if not articles: print(f"  No more articles on NewsAPI page {page_num}."); break
        page_added_count = 0
        for article in articles:
            link = article.get('url')
            if link and link not in processed_links:
                processed_links.add(link)
                timestamp = format_timestamp(article.get('publishedAt'))
                summary = clean_html_summary(article.get('description') or article.get('content'))
                title = clean_html_summary(article.get('title', 'N/A'))
                if not title or title == 'N/A': continue
                if summary and len(summary) > 500: summary = summary[:500] + "..."
                formatted_item = { 'title': title.strip(), 'url': link, 'summary': summary, 'timestamp': timestamp, 'source_name': f"NewsAPI ({article.get('source', {}).get('name', 'Unknown')})" }
                all_news.append(formatted_item); page_added_count += 1
        print(f"  Added {page_added_count} unique items from NewsAPI page {page_num}.")
        total_results = response.get('totalResults', 0)
        if page_num * NEWSAPI_PAGE_SIZE >= total_results: print("  Reached estimated total NewsAPI results."); break
    print(f"--- Finished NewsAPI fetching. Found {len(all_news)} unique items. ---")
    return all_news

def get_yfinance_news(tickers):
    # ...(Keep existing get_yfinance_news function - acknowledge unreliability)...
    if not YFINANCE_AVAILABLE: return []
    print(f"\n--- Fetching news from Yahoo Finance (yfinance) for {len(tickers)} tickers ---")
    print("    (Note: yfinance news fetching can be unreliable)")
    all_news = []; processed_links = set()
    session = requests.Session() if REQUESTS_AVAILABLE else None
    if session: session.headers.update({'User-Agent': 'Mozilla/5.0'})
    for ticker_symbol in tickers:
        print(f"  Fetching news for {ticker_symbol}...")
        news_list = None
        try: ticker = yf.Ticker(ticker_symbol, session=session) if session else yf.Ticker(ticker_symbol); news_list = ticker.news
        except Exception as e: print(f"    ERROR getting yfinance .news for {ticker_symbol}: {e}"); time.sleep(0.1); continue
        if not news_list: print(f"    No news found via yfinance for {ticker_symbol}."); continue
        count = 0
        for news_item in news_list:
            if not isinstance(news_item, dict): print(f"    Warn: Unexpected yfinance item: {news_item}"); continue
            if count >= MAX_ARTICLES_PER_TICKER: break
            link = news_item.get('link')
            if link and 'guce.yahoo' in link:
                 match = re.search(r'url=([^&]+)', link)
                 if match:
                    try: link = requests.utils.unquote(match.group(1))
                    except Exception: link = html.unescape(match.group(1))
            if link and link not in processed_links:
                processed_links.add(link)
                timestamp = format_timestamp(news_item.get('providerPublishTime'))
                title = clean_html_summary(news_item.get('title', 'N/A'))
                publisher = news_item.get('publisher', 'N/A')
                if not title or title == 'N/A': continue
                formatted_item = { 'title': title.strip(), 'url': link, 'summary': f"Publisher: {publisher}", 'timestamp': timestamp, 'related_ticker': ticker_symbol, 'source_name': 'Yahoo Finance (yfinance)' }
                all_news.append(formatted_item); count += 1
        print(f"    Fetched {count} valid items for {ticker_symbol}.")
        time.sleep(REQUEST_DELAY_SOURCES / 3)
    print(f"--- Finished yfinance fetching. Found {len(all_news)} items. ---")
    return all_news

def get_vix_value_yfinance():
    """Fetches the latest VIX value using yfinance. Returns float or None."""
    if not YFINANCE_AVAILABLE: print("Warn: yfinance not available, cannot fetch VIX."); return None
    print("\n--- Fetching VIX Value ---")
    try:
        vix_ticker = yf.Ticker("^VIX")
        hist = vix_ticker.history(period="5d")
        if hist.empty: print("  ERROR: yfinance returned empty history for ^VIX."); return None
        latest_vix = hist['Close'].iloc[-1]
        print(f"  Fetched VIX value (likely previous close): {latest_vix:.2f}")
        return float(latest_vix)
    except Exception as e: print(f"  ERROR fetching VIX value using yfinance: {e}"); return None

# --- Main Execution Logic ---

if __name__ == "__main__":
    print("Starting news aggregation and VIX fetching process...")
    start_time = time.time()
    master_news_list = []
    fetched_vix = None # Initialize VIX value

    # --- Fetch VIX Value First (or concurrently if using async) ---
    # Fetching VIX here ensures it's included even if news fetching fails partially
    fetched_vix = get_vix_value_yfinance()

    # --- Fetch News Articles ---
    rss_items = get_rss_news(); master_news_list.extend(rss_items); time.sleep(REQUEST_DELAY_SOURCES)
    newsapi_items = get_newsapi_news(); master_news_list.extend(newsapi_items); time.sleep(REQUEST_DELAY_SOURCES)
    # yfinance_items = get_yfinance_news(YAHOO_TICKERS); master_news_list.extend(yfinance_items) # Keep commented out if unreliable

    # --- Process and Prepare Final Output ---
    print("\n--- Processing Combined Results ---")
    unique_news = []
    if master_news_list:
        print(f"Total fetched before deduplication: {len(master_news_list)}")
        seen_urls = set()
        for item in master_news_list:
            url = item.get('url')
            if url:
                try:
                    norm_url = url.lower().replace("https://", "").replace("http://", "").replace("www.", "")
                    norm_url = norm_url.split('?')[0].split('#')[0].rstrip('/')
                    if norm_url and norm_url not in seen_urls:
                        if not item.get('timestamp'): item['timestamp'] = datetime(1970, 1, 1, tzinfo=timezone.utc).isoformat() + 'Z'; print(f"  Warn: Missing ts for URL {url}.")
                        if isinstance(item.get('timestamp'), str) and 'T' in item['timestamp']: unique_news.append(item); seen_urls.add(norm_url)
                        else: print(f"  Warn: Skipping item with invalid ts format '{item.get('timestamp')}' for URL {url}")
                except Exception as e: print(f"  Error normalizing URL {url}: {e}. Skipping.")
        print(f"Total unique articles after deduplication: {len(unique_news)}")
        try:
            unique_news.sort( key=lambda x: datetime.fromisoformat(x['timestamp'].replace('Z', '+00:00')), reverse=True )
            print("Sorted articles by timestamp (newest first).")
        except Exception as sort_e: print(f"Warn: Could not sort articles: {sort_e}.")
        if len(unique_news) > MAX_TOTAL_ARTICLES: print(f"Limiting articles from {len(unique_news)} to {MAX_TOTAL_ARTICLES}."); unique_news = unique_news[:MAX_TOTAL_ARTICLES]
    else:
        print("\nNo news articles were successfully fetched from any source.")

    # --- Create Final Output Dictionary ---
    vix_timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds') + 'Z'
    output_data = {
        "vix_data": {
            "vix": fetched_vix, # Will be None if fetching failed
            "timestamp_utc": vix_timestamp # Timestamp when VIX was attempted/fetched
        },
        "articles": unique_news # Contains the processed list of news articles
    }

    # --- Save Combined Data to JSON ---
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_filepath = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\nCombined news and VIX data saved to {output_filepath}")
    except Exception as e:
        print(f"An error occurred saving combined file to {os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)}: {e}")


    end_time = time.time()
    print(f"\nWeb scraping process finished in {end_time - start_time:.2f} seconds.")
    #TEST COMMIT