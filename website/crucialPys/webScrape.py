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

# EXPANDED RSS FEEDS (NO API KEY REQUIRED)
ALL_RSS_FEEDS = [
    ('Google News Finance', 'https://news.google.com/rss/search?q=finance+stock+market+when%3A1d&hl=en-US&gl=US&ceid=US%3Aen'),
    ('Yahoo Finance Market News', 'https://finance.yahoo.com/news/rssindex'),
    ('Investing.com News', 'https://www.investing.com/rss/news.rss'),
    ('MarketWatch Top Stories', 'https://feeds.marketwatch.com/marketwatch/topstories/'),
    ('CNBC Top News', 'https://www.cnbc.com/id/100003114/device/rss/rss.html'),
    ('Reuters Business', 'http://feeds.reuters.com/reuters/businessNews'),
    ('Fortune Markets', 'https://fortune.com/sector/markets/feed/'),
    ('Seeking Alpha Market Currents', 'https://seekingalpha.com/market_currents.xml'),
    ('Financial Times Markets', 'https://www.ft.com/markets?format=rss'),
    ('WSJ Business', 'https://feeds.a.dj.com/rss/WSJArticles.xml')
]

MAX_ARTICLES_PER_FEED = 25
YAHOO_TICKERS = ['^GSPC', '^IXIC', '^DJI', '^VIX', 'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META']
MAX_ARTICLES_PER_TICKER = 10
MAX_TOTAL_ARTICLES = 300

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(WEBSITE_DIR, "data_files")
OUTPUT_FILENAME = "financial_news_agg.json"

MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 15

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

def format_timestamp(date_input):
    if not date_input: return None
    dt_utc = None
    if isinstance(date_input, (int, float)):
        try:
            ts = float(date_input)
            if ts > 1e11: ts /= 1000.0
            dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception: return None
    elif isinstance(date_input, str):
        formats = ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%SZ', '%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%d %H:%M:%S']
        for fmt in formats:
            try:
                dt_utc = datetime.strptime(date_input, fmt).astimezone(timezone.utc)
                break
            except Exception: continue
    elif isinstance(date_input, time.struct_time):
        dt_utc = datetime(*date_input[:6], tzinfo=timezone.utc)
    
    return dt_utc.isoformat(timespec='seconds').replace('+00:00', 'Z') if dt_utc else None

def get_rss_news():
    if not FEEDPARSER_AVAILABLE or not REQUESTS_AVAILABLE: return []
    all_news, processed_links = [], set()
    for source_name, url in ALL_RSS_FEEDS:
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=REQUEST_TIMEOUT)
            feed = feedparser.parse(response.content)
            count = 0
            for entry in feed.entries:
                if count >= MAX_ARTICLES_PER_FEED: break
                link = entry.get('link')
                if link and link not in processed_links:
                    processed_links.add(link)
                    all_news.append({
                        'title': clean_html_summary(entry.get('title', 'N/A')),
                        'url': link,
                        'summary': clean_html_summary(entry.get('description', entry.get('summary', 'N/A'))),
                        'timestamp': format_timestamp(entry.get('published_parsed') or entry.get('published')),
                        'source_name': f"RSS ({source_name})"
                    })
                    count += 1
        except Exception: continue
    return all_news

def get_yfinance_news(tickers):
    if not YFINANCE_AVAILABLE: return []
    all_news, processed_links = [], set()
    for ticker_symbol in tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            news_list = ticker.news
            count = 0
            for news_item in news_list:
                if count >= MAX_ARTICLES_PER_TICKER: break
                link = news_item.get('link')
                if link and link not in processed_links:
                    processed_links.add(link)
                    all_news.append({
                        'title': clean_html_summary(news_item.get('title', 'N/A')),
                        'url': link,
                        'summary': f"Publisher: {news_item.get('publisher', 'N/A')}",
                        'timestamp': format_timestamp(news_item.get('providerPublishTime')),
                        'source_name': 'Yahoo Finance'
                    })
                    count += 1
        except Exception: continue
    return all_news

def get_vix_value():
    # 1. Try yfinance primary method
    if YFINANCE_AVAILABLE:
        try:
            ticker = yf.Ticker("^VIX")
            hist = ticker.history(period="5d", timeout=5)
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
        except Exception: pass
        
        # 2. Try yfinance fast_info
        try:
            ticker = yf.Ticker("^VIX")
            if hasattr(ticker, 'fast_info'):
                val = ticker.fast_info.get('last_price')
                if val: return float(val)
        except Exception: pass

    # 3. Final Fallback: Try CNBC public quote API (very reliable for indices)
    if REQUESTS_AVAILABLE:
        try:
            # CNBC public API endpoint for indices
            url = "https://quote.cnbc.com/quote-html-webservice/quote.htm?symbols=.VIX&output=json&noform=1&partnerId=2"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                root = data.get('QuickQuoteResult') or data.get('ExtendedQuoteResult')
                price = None
                if root:
                    extended_quotes = root.get('ExtendedQuote')
                    if extended_quotes and isinstance(extended_quotes, list) and len(extended_quotes) > 0:
                        price = extended_quotes[0].get('QuickQuote', {}).get('last')
                    else:
                        # Handle case-sensitivity (some versions use 'QuickQuote', some 'quickquote')
                        quickquote = root.get('QuickQuote') or root.get('quickquote')
                        if isinstance(quickquote, list) and len(quickquote) > 0:
                            price = quickquote[0].get('last')
                        elif isinstance(quickquote, dict):
                            price = quickquote.get('last')
                    
                    if price:
                        return float(price)
        except Exception: pass

    # 4. Emergency Fallback: Stooq
    if REQUESTS_AVAILABLE:
        try:
            url = "https://stooq.com/q/l/?s=%5evix&f=sd2t2ohlcv&h&e=csv"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                lines = response.text.strip().split('\n')
                if len(lines) > 1:
                    data = lines[1].split(',')
                    if len(data) >= 7 and data[6] != 'N/D':
                        return float(data[6])
        except Exception: pass
        
    return None

if __name__ == "__main__":
    print("Scraping live news (no API keys required)...")
    master_news_list = get_rss_news() + get_yfinance_news(YAHOO_TICKERS)
    vix = get_vix_value()
    
    unique_news = []
    seen_urls = set()
    for item in master_news_list:
        url = item.get('url')
        if url and url not in seen_urls:
            unique_news.append(item)
            seen_urls.add(url)
    
    unique_news.sort(key=lambda x: x['timestamp'] or '', reverse=True)
    if len(unique_news) > MAX_TOTAL_ARTICLES: unique_news = unique_news[:MAX_TOTAL_ARTICLES]

    output_data = {
        "vix_data": { "vix": vix, "timestamp_utc": datetime.now(timezone.utc).isoformat() + 'Z' },
        "articles": unique_news
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, OUTPUT_FILENAME), 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"Success! {len(unique_news)} articles scraped.")
