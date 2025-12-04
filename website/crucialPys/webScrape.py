import json
import time
import os
import html
import re
import sys
from datetime import datetime, timezone, timedelta

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

try:
    from newsapi import NewsApiClient, NewsAPIException
    NEWSAPI_AVAILABLE = True
except ImportError:
    NEWSAPI_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

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
YAHOO_TICKERS = ['^GSPC', '^IXIC', '^DJI', '^VIX', 'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'JPM', 'BAC', 'XOM', 'CVX', 'WMT', 'COST']
MAX_ARTICLES_PER_TICKER = 5
MAX_TOTAL_ARTICLES = 250

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(WEBSITE_DIR, "data_files")
OUTPUT_FILENAME = "financial_news_agg.json"

MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 15
REQUEST_DELAY_SOURCES = 0.5
RSS_FETCH_DELAY_FEEDS = 0.2

def clean_html_summary(summary_html):
    if not summary_html or not isinstance(summary_html, str):
        return "N/A"
    
    summary_text = summary_html
    if BS4_AVAILABLE and ('<' in summary_text and '>' in summary_text):
        try:
            soup = BeautifulSoup(summary_html, "html.parser")
            summary_text = ' '.join(soup.stripped_strings)
        except Exception:
            summary_text = re.sub('<[^<]+?>', ' ', summary_html)
            summary_text = ' '.join(summary_text.split())
    elif '<' in summary_text and '>' in summary_text:
        summary_text = re.sub('<[^<]+?>', ' ', summary_html)
        summary_text = ' '.join(summary_text.split())
    
    return html.unescape(summary_text).strip()

def format_timestamp_from_parsed(parsed_time):
    if not parsed_time:
        return None
    try:
        import calendar
        utc_timestamp = calendar.timegm(parsed_time)
        dt_utc = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
        return dt_utc.isoformat(timespec='seconds').replace('+00:00', 'Z')
    except (ValueError, TypeError, OverflowError):
        return None

def format_timestamp(date_input):
    if not date_input:
        return None

    dt_utc = None

    if isinstance(date_input, (int, float)):
        try:
            timestamp_val = float(date_input)
            if timestamp_val > 1e11:
                timestamp_val /= 1000.0
            dt_utc = datetime.fromtimestamp(timestamp_val, tz=timezone.utc)
        except (ValueError, OSError):
            return None
            
    elif isinstance(date_input, str):
        date_str = date_input.strip()
        formats_to_try = [
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%a, %d %b %Y %H:%M:%S %z',
            '%a, %d %b %Y %H:%M:%S %Z',
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S'
        ]

        if sys.version_info < (3, 7):
            formats_to_try = [f.replace('%f%z', '%f').replace('%S%z', '%S') if '%z' in f and ':' in date_str else f for f in formats_to_try]

        for fmt in formats_to_try:
            try:
                dt_naive_or_aware = datetime.strptime(date_str, fmt)
                if dt_naive_or_aware.tzinfo is None or dt_naive_or_aware.tzinfo.utcoffset(dt_naive_or_aware) is None:
                    dt_utc = dt_naive_or_aware.replace(tzinfo=timezone.utc)
                else:
                    dt_utc = dt_naive_or_aware.astimezone(timezone.utc)
                break
            except (ValueError, TypeError):
                continue
        
        if not dt_utc and date_str.isdigit():
            try:
                ts_val = int(date_str)
                if ts_val > 1e11:
                    ts_val /= 1000.0
                dt_utc = datetime.fromtimestamp(ts_val, tz=timezone.utc)
            except (ValueError, OSError):
                pass

    elif isinstance(date_input, time.struct_time):
        iso_string = format_timestamp_from_parsed(date_input)
        if iso_string:
            try:
                dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
            except ValueError:
                return None

    if dt_utc:
        return dt_utc.isoformat(timespec='seconds').replace('+00:00', 'Z')
    
    return None

def fetch_url_with_retry(url, headers=None):
    if not REQUESTS_AVAILABLE:
        return None
        
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.exceptions.HTTPError) and 400 <= e.response.status_code < 500:
                break
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                
    return None

def get_rss_news():
    if not FEEDPARSER_AVAILABLE or not REQUESTS_AVAILABLE:
        return []
        
    all_news = []
    processed_links = set()
    
    for source_name, url in ALL_RSS_FEEDS:
        headers = {'User-Agent': 'Mozilla/5.0'}
        rss_content = fetch_url_with_retry(url, headers)
        
        if not rss_content:
            continue

        try:
            feed = feedparser.parse(rss_content)
            if not feed.entries:
                continue

            count = 0
            for entry in feed.entries:
                if count >= MAX_ARTICLES_PER_FEED:
                    break
                    
                link = entry.get('link')
                if link and link not in processed_links:
                    processed_links.add(link)
                    timestamp_raw = entry.get('published_parsed') or entry.get('updated_parsed') or entry.get('published') or entry.get('updated')
                    timestamp = format_timestamp(timestamp_raw)
                    
                    summary_raw = entry.get('description', entry.get('summary', 'N/A'))
                    summary = clean_html_summary(summary_raw)
                    title = clean_html_summary(entry.get('title', 'N/A'))
                    
                    if not title or title == 'N/A':
                        continue

                    if source_name.startswith('Google News'):
                        title = re.sub(r'\s+-\s+[^-]+$', '', title).strip()

                    publisher = entry.get('source', {}).get('title')
                    source_display_name = f"Google News ({publisher})" if source_name.startswith('Google News') and publisher else f"RSS ({source_name})"

                    all_news.append({
                        'title': title, 
                        'url': link, 
                        'summary': summary, 
                        'timestamp': timestamp, 
                        'source_name': source_display_name
                    })
                    count += 1
        except Exception:
            pass
            
        time.sleep(RSS_FETCH_DELAY_FEEDS)
        
    return all_news

def get_newsapi_news():
    if not NEWSAPI_AVAILABLE:
        return []
    if not NEWSAPI_KEY:
        return []
        
    all_news = []
    processed_links = set()
    newsapi = NewsApiClient(api_key=NEWSAPI_KEY)
    from_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')

    for page_num in range(1, NEWSAPI_MAX_PAGES + 1):
        response = None
        success = False
        
        for attempt in range(MAX_RETRIES):
            try:
                response = newsapi.get_everything(
                    q=NEWSAPI_QUERY,
                    sources=NEWSAPI_SOURCES,
                    language=NEWSAPI_LANGUAGE,
                    sort_by=NEWSAPI_SORT_BY,
                    page_size=NEWSAPI_PAGE_SIZE,
                    page=page_num,
                    from_param=from_date
                )
                success = True
                break
            except NewsAPIException as e:
                if e.get_code() in ['rateLimited', 'maximumResultsReached', 'apiKeyInvalid', 'apiKeyDisabled']:
                    page_num = NEWSAPI_MAX_PAGES
                    success = False
                    break
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
            except Exception:
                time.sleep(RETRY_DELAY * (attempt + 1))

        if not success or response is None or response.get('status') != 'ok':
            break

        articles = response.get('articles', [])
        if not articles:
            break

        for article in articles:
            link = article.get('url')
            if link and link not in processed_links:
                processed_links.add(link)
                timestamp = format_timestamp(article.get('publishedAt'))
                summary = clean_html_summary(article.get('description') or article.get('content'))
                title = clean_html_summary(article.get('title', 'N/A'))
                
                if not title or title == 'N/A':
                    continue

                if summary and len(summary) > 500:
                    summary = summary[:500] + "..."

                all_news.append({
                    'title': title.strip(),
                    'url': link,
                    'summary': summary,
                    'timestamp': timestamp,
                    'source_name': f"NewsAPI ({article.get('source', {}).get('name', 'Unknown')})"
                })

        total_results = response.get('totalResults', 0)
        if page_num * NEWSAPI_PAGE_SIZE >= total_results:
            break
            
    return all_news

def get_yfinance_news(tickers):
    if not YFINANCE_AVAILABLE:
        return []
        
    all_news = []
    processed_links = set()
    session = requests.Session() if REQUESTS_AVAILABLE else None
    if session:
        session.headers.update({'User-Agent': 'Mozilla/5.0'})

    for ticker_symbol in tickers:
        try:
            ticker = yf.Ticker(ticker_symbol, session=session) if session else yf.Ticker(ticker_symbol)
            news_list = ticker.news
        except Exception:
            time.sleep(0.1)
            continue

        if not news_list:
            continue

        count = 0
        for news_item in news_list:
            if not isinstance(news_item, dict):
                continue
                
            if count >= MAX_ARTICLES_PER_TICKER:
                break
                
            link = news_item.get('link')
            if link and 'guce.yahoo' in link:
                 match = re.search(r'url=([^&]+)', link)
                 if match:
                    try:
                        link = requests.utils.unquote(match.group(1))
                    except Exception:
                        link = html.unescape(match.group(1))

            if link and link not in processed_links:
                processed_links.add(link)
                timestamp = format_timestamp(news_item.get('providerPublishTime'))
                title = clean_html_summary(news_item.get('title', 'N/A'))
                publisher = news_item.get('publisher', 'N/A')
                
                if not title or title == 'N/A':
                    continue

                all_news.append({
                    'title': title.strip(),
                    'url': link,
                    'summary': f"Publisher: {publisher}",
                    'timestamp': timestamp,
                    'related_ticker': ticker_symbol,
                    'source_name': 'Yahoo Finance (yfinance)'
                })
                count += 1
                
        time.sleep(REQUEST_DELAY_SOURCES / 3)
        
    return all_news

def get_vix_value_yfinance():
    if not YFINANCE_AVAILABLE:
        return None
        
    try:
        vix_ticker = yf.Ticker("^VIX")
        hist = vix_ticker.history(period="5d")
        
        if hist.empty:
            info = vix_ticker.info
            latest_vix = info.get('regularMarketPreviousClose') or info.get('previousClose') or info.get('regularMarketPrice')
            if latest_vix:
                 return float(latest_vix)
            else:
                return None

        latest_vix = hist['Close'].iloc[-1]
        return float(latest_vix)
    except Exception:
        return None

if __name__ == "__main__":
    start_time = time.time()
    master_news_list = []
    
    fetched_vix = get_vix_value_yfinance()

    rss_items = get_rss_news()
    master_news_list.extend(rss_items)
    time.sleep(REQUEST_DELAY_SOURCES)
    
    newsapi_items = get_newsapi_news()
    master_news_list.extend(newsapi_items)
    time.sleep(REQUEST_DELAY_SOURCES)

    unique_news = []
    if master_news_list:
        seen_urls = set()
        for item in master_news_list:
            url = item.get('url')
            if url:
                try:
                    norm_url = url.lower().replace("https://", "").replace("http://", "").replace("www.", "")
                    norm_url = norm_url.split('?')[0].split('#')[0].rstrip('/')
                    
                    if norm_url and norm_url not in seen_urls:
                        ts_str = item.get('timestamp')
                        if not ts_str or not isinstance(ts_str, str) or 'T' not in ts_str:
                             item['timestamp'] = datetime(1970, 1, 1, tzinfo=timezone.utc).isoformat(timespec='seconds') + 'Z'

                        if isinstance(item.get('timestamp'), str) and 'T' in item['timestamp']:
                            unique_news.append(item)
                            seen_urls.add(norm_url)
                except Exception:
                    pass

        try:
            unique_news.sort(
                 key=lambda x: datetime.fromisoformat(x['timestamp'].replace('Z', '+00:00')) if isinstance(x.get('timestamp'), str) and 'T' in x['timestamp'] else datetime.min.replace(tzinfo=timezone.utc),
                 reverse=True
            )
        except Exception:
            pass

        if len(unique_news) > MAX_TOTAL_ARTICLES:
            unique_news = unique_news[:MAX_TOTAL_ARTICLES]

    vix_timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds') + 'Z'
    output_data = {
        "vix_data": { "vix": fetched_vix, "timestamp_utc": vix_timestamp },
        "articles": unique_news
    }

    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_filepath = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving file: {e}")
