import json # pentru lucrul cu date json
import time # pentru functii legate de timp, ex. sleep
from datetime import datetime, timezone, timedelta # pentru lucrul cu date si ore, fusuri orare
import os # pentru interactiunea cu sistemul de operare (cai fisiere, variabile de mediu)
import html # pentru decodarea entitatilor html
import re # pentru expresii regulate (cautare si manipulare de text)
import sys # pentru informatii specifice sistemului, ex. versiunea python

# incercam sa importam bibliotecile optionale si setam flag-uri pentru disponibilitatea lor
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

# cheia api pentru newsapi, citita din variabilele de mediu
NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY')

# avertisment daca cheia newsapi nu este gasita
if not NEWSAPI_KEY:
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("!!! CRITICAL WARNING: NEWSAPI_KEY not found in environment variables!")
    print("!!! NewsAPI fetching will fail.")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

# configurari pentru interogarea newsapi
NEWSAPI_QUERY = '(finance OR stock market OR economy OR investing OR earnings OR fed OR rates) AND (market OR stocks OR business)' # interogarea de cautare
NEWSAPI_SOURCES = 'bloomberg,reuters,the-wall-street-journal,financial-post,cnbc,business-insider,fortune,associated-press' # surse de stiri
NEWSAPI_LANGUAGE = 'en' # limba articolelor
NEWSAPI_SORT_BY = 'publishedAt' # criteriul de sortare
NEWSAPI_PAGE_SIZE = 50 # numarul de articole pe pagina
NEWSAPI_MAX_PAGES = 3 # numarul maxim de pagini de preluat

# lista de fluxuri rss generale
RSS_FEEDS_GENERAL = [ ('Google News (Reuters Site)', 'https://news.google.com/rss/search?q=site%3Areuters.com+when%3A1d&hl=en-US&gl=US&ceid=US%3Aen'), ('Yahoo Finance Market News', 'https://finance.yahoo.com/news/rssindex'), ]
# lista de fluxuri rss specifice pietelor financiare
RSS_FEEDS_MARKETS = [ ('Investing.com News', 'https://www.investing.com/rss/news.rss'), ('MarketWatch Top Stories', 'https://feeds.marketwatch.com/marketwatch/topstories/'), ('CNBC Top News', 'https://www.cnbc.com/id/100003114/device/rss/rss.html'), ('Seeking Alpha Market Currents', 'https://seekingalpha.com/market_currents.xml'), ]
# lista combinata a tuturor fluxurilor rss
ALL_RSS_FEEDS = RSS_FEEDS_GENERAL + RSS_FEEDS_MARKETS
MAX_ARTICLES_PER_FEED = 20 # numarul maxim de articole de preluat per flux rss
# lista de simboluri bursiere pentru yahoo finance
YAHOO_TICKERS = [ '^GSPC', '^IXIC', '^DJI', '^VIX', 'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'JPM', 'BAC', 'XOM', 'CVX', 'WMT', 'COST' ]
MAX_ARTICLES_PER_TICKER = 5 # numarul maxim de articole de preluat per simbol bursier
MAX_TOTAL_ARTICLES = 250 # numarul maxim total de articole de salvat
OUTPUT_FILENAME = "financial_news_agg.json" # numele fisierului de iesire
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # directorul scriptului curent
WEBSITE_DIR = os.path.dirname(SCRIPT_DIR) # directorul parinte (presupus a fi directorul website-ului)
OUTPUT_DIR = os.path.join(WEBSITE_DIR, "data_files") # directorul de iesire pentru fisierele de date

# configurari pentru reincercari si timeout-uri
MAX_RETRIES = 3 # numarul maxim de reincercari pentru cereri esuate
RETRY_DELAY = 2 # intarziere intre reincercari (secunde)
REQUEST_TIMEOUT = 15 # timeout pentru cererile http (secunde)
REQUEST_DELAY_SOURCES = 0.5 # intarziere intre preluarea de la diferite surse (secunde)
RSS_FETCH_DELAY_FEEDS = 0.2 # intarziere intre preluarea diferitelor fluxuri rss (secunde)

def clean_html_summary(summary_html):
    # curata un rezumat html, eliminand tag-urile si decodand entitatile html
    if not summary_html or not isinstance(summary_html, str): return "N/A" # trateaza cazurile nule sau de tip incorect
    summary_text = summary_html
    # daca beautifulsoup este disponibil si textul pare a fi html, il folosim pentru curatare
    if BS4_AVAILABLE and '<' in summary_text and '>' in summary_text:
        try: soup = BeautifulSoup(summary_html, "html.parser"); summary_text = ' '.join(soup.stripped_strings)
        except Exception as e: print(f"  Warn: BS4 parse failed: {e}. Falling back."); summary_text = re.sub('<[^<]+?>', ' ', summary_html); summary_text = ' '.join(summary_text.split()) # fallback la regex daca bs4 esueaza
    # daca bs4 nu e disponibil dar textul pare html, folosim regex
    elif '<' in summary_text and '>' in summary_text: summary_text = re.sub('<[^<]+?>', ' ', summary_html); summary_text = ' '.join(summary_text.split())
    return html.unescape(summary_text).strip() # decodam entitatile html ramase si eliminam spatiile de la margini

def format_timestamp_from_parsed(parsed_time):
    # formateaza un timestamp dintr-un obiect time.struct_time (produs de feedparser) in format iso 8601 utc
    if not parsed_time: return None
    try:
        # importa calendar aici pentru a evita dependenta globala daca functia nu e folosita des
        import calendar
        # converteste struct_time la un timestamp unix utc
        utc_timestamp = calendar.timegm(parsed_time)
        # converteste timestamp-ul unix la un obiect datetime utc
        dt_utc = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
        # formateaza in iso 8601 cu 'z' pentru utc
        return dt_utc.isoformat(timespec='seconds').replace('+00:00', 'Z')
    except (ValueError, TypeError, OverflowError) as e:
        print(f"  Warn: Could not format from struct_time {parsed_time}: {e}")
        return None

def format_timestamp(date_input):
    """
    converteste diverse tipuri de input pentru data (timestamp numeric, string, time.struct_time)
    intr-un format string iso 8601 standardizat (aaaa-ll-zzthh:mm:ssz) in utc.

    args:
        date_input: data/ora de formatat. poate fi int/float (timestamp unix),
                    str (diverse formate), sau time.struct_time.

    returns:
        str: string-ul formatat iso 8601 in utc, sau none daca parsarea esueaza.
    """
    if not date_input:
        return None # returneaza none daca input-ul este gol

    dt_utc = None # initializam obiectul datetime utc

    # daca input-ul este un numar (timestamp unix)
    if isinstance(date_input, (int, float)):
        try:
            timestamp_val = float(date_input)
            # normalizeaza timestamp-ul daca este in milisecunde
            if timestamp_val > 1e11: # o valoare euristica pentru a detecta milisecunde
                timestamp_val /= 1000.0
            dt_utc = datetime.fromtimestamp(timestamp_val, tz=timezone.utc)
        except (ValueError, OSError) as e:
            print(f"  Warn: Could not parse numeric timestamp '{date_input}': {e}")
            return None
    # daca input-ul este un string
    elif isinstance(date_input, str):
        date_str = date_input.strip() # eliminam spatiile de la margini

        # lista de formate de data pe care sa le incercam
        formats_to_try = [
            '%Y-%m-%dT%H:%M:%S.%f%z', # iso 8601 cu microsecunde si fus orar
            '%Y-%m-%dT%H:%M:%S%z',    # iso 8601 cu fus orar
            '%Y-%m-%dT%H:%M:%S.%fZ',  # iso 8601 cu microsecunde si 'z'
            '%Y-%m-%dT%H:%M:%SZ',     # iso 8601 cu 'z'
            '%a, %d %b %Y %H:%M:%S %z', # format rfc 822 / 1123
            '%a, %d %b %Y %H:%M:%S %Z', # format rfc 822 / 1123 cu nume fus orar
            '%Y-%m-%d %H:%M:%S',      # format comun fara fus orar
            '%Y/%m/%d %H:%M:%S'       # alt format comun fara fus orar
        ]

        # ajustam formatele pentru python < 3.7 care nu suporta ':' in %z
        if sys.version_info < (3, 7):
            formats_to_try = [f.replace('%f%z', '%f').replace('%S%z', '%S') if '%z' in f and ':' in date_str else f for f in formats_to_try]

        parsed_successfully = False
        for fmt in formats_to_try:
            try:
                dt_naive_or_aware = datetime.strptime(date_str, fmt) # incercam sa parsam string-ul

                # daca obiectul datetime este naiv (fara fus orar), il consideram utc
                if dt_naive_or_aware.tzinfo is None or dt_naive_or_aware.tzinfo.utcoffset(dt_naive_or_aware) is None:
                    dt_utc = dt_naive_or_aware.replace(tzinfo=timezone.utc)
                else:
                    # daca are fus orar, il convertim la utc
                    dt_utc = dt_naive_or_aware.astimezone(timezone.utc)
                parsed_successfully = True
                break # iesim din bucla daca parsarea a reusit
            except (ValueError, TypeError):
                continue # incercam urmatorul format

        # daca niciun format nu s-a potrivit, incercam sa parsam ca timestamp numeric (daca e string de cifre)
        if not parsed_successfully:
            if date_str.isdigit():
                try:
                    ts_val = int(date_str)
                    if ts_val > 1e11: # posibil milisecunde
                        ts_val /= 1000.0
                    dt_utc = datetime.fromtimestamp(ts_val, tz=timezone.utc)
                    parsed_successfully = True
                except (ValueError, OSError):
                    pass # esuat si aici

        if not parsed_successfully:
            print(f"  Warn: Could not parse string timestamp format: '{date_input}'")
            return None
    # daca input-ul este un obiect time.struct_time (de la feedparser)
    elif isinstance(date_input, time.struct_time):
        # folosim functia dedicata pentru struct_time
        iso_string = format_timestamp_from_parsed(date_input)
        if iso_string:
            # re-parsam string-ul iso pentru a obtine un obiect datetime consistent
            try:
                dt_utc = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
            except ValueError:
                 print(f"  Warn: Could not re-parse from struct_time result: '{iso_string}'")
                 return None
        else:
            return None # format_timestamp_from_parsed a esuat
    else:
        # tip de data neasteptat
        print(f"  Warn: Unhandled timestamp type: {type(date_input)} value: {date_input}")
        return None

    if dt_utc:
        # formateaza obiectul datetime in iso 8601, cu 'z' pentru utc
        return dt_utc.isoformat(timespec='seconds').replace('+00:00', 'Z')
    else:
        # nu s-a putut crea dt_utc
        return None

def fetch_url_with_retry(url, headers=None):
    # preia continutul unei url, cu reincercari in caz de eroare
    if not REQUESTS_AVAILABLE: print("  ERROR: 'requests' needed."); return None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT) # efectueaza cererea get
            response.raise_for_status() # ridica o exceptie pentru coduri de stare http 4xx/5xx
            return response.content # returneaza continutul raspunsului
        except requests.exceptions.RequestException as e:
            print(f"  Attempt {attempt+1}/{MAX_RETRIES}: Error fetch {url}: {e}")
            # daca este o eroare client (4xx), nu mai reincerca
            if isinstance(e, requests.exceptions.HTTPError) and 400 <= e.response.status_code < 500:
                print(f"  Client error {e.response.status_code}, stopping retry."); break
        if attempt < MAX_RETRIES - 1: time.sleep(RETRY_DELAY) # asteapta inainte de urmatoarea reincercare
    print(f"  ERROR: Failed fetch {url} after {MAX_RETRIES} attempts."); return None # esuat dupa toate reincercarile

def get_rss_news():
    # preia stiri din fluxurile rss configurate
    if not FEEDPARSER_AVAILABLE or not REQUESTS_AVAILABLE: return [] # verifica dependentele
    print("\n--- Fetching news from RSS Feeds ---")
    all_news = [] # lista pentru a stoca toate stirile
    processed_links = set() # set pentru a urmari link-urile procesate si a evita duplicatele
    for source_name, url in ALL_RSS_FEEDS:
        print(f"Fetching feed: {source_name} ({url})")
        headers = {'User-Agent': 'Mozilla/5.0'} # user-agent pentru a evita blocarea
        rss_content = fetch_url_with_retry(url, headers) # preia continutul rss
        if not rss_content: print(f"  Skipping feed '{source_name}' due to fetch error."); continue # sare peste flux daca preluarea esueaza

        try:
            feed = feedparser.parse(rss_content) # parseaza continutul rss
            if feed.bozo: print(f"  Warn: Feed '{source_name}' ill-formed: {feed.bozo_exception}") # avertisment daca fluxul e malformat
            if not feed.entries: print(f"  Info: Feed '{source_name}' empty."); continue # informeaza daca fluxul e gol

            count = 0 # contor pentru articole per flux
            for entry in feed.entries:
                if count >= MAX_ARTICLES_PER_FEED: break # limiteaza numarul de articole per flux
                link = entry.get('link')
                if link and link not in processed_links: # verifica daca link-ul exista si nu a fost procesat
                    processed_links.add(link) # adauga link-ul la setul de link-uri procesate
                    # obtine timestamp-ul, incercand mai multe campuri posibile
                    timestamp_raw = entry.get('published_parsed') or entry.get('updated_parsed') or entry.get('published') or entry.get('updated')
                    timestamp = format_timestamp(timestamp_raw) # formateaza timestamp-ul
                    # obtine rezumatul, incercand mai multe campuri posibile
                    summary_raw = entry.get('description', entry.get('summary', 'N/A'))
                    summary = clean_html_summary(summary_raw) # curata rezumatul html
                    title = clean_html_summary(entry.get('title', 'N/A')) # curata titlul html
                    if not title or title == 'N/A': continue # sare peste articol daca nu are titlu

                    # ajusteaza titlul pentru stirile de la google news (elimina sufixul sursei)
                    if source_name.startswith('Google News'):
                        title = re.sub(r'\s+-\s+[^-]+$', '', title).strip()

                    # determina numele sursei afisate
                    publisher = entry.get('source', {}).get('title')
                    source_display_name = f"Google News ({publisher})" if source_name.startswith('Google News') and publisher else f"RSS ({source_name})"

                    # creeaza un dictionar formatat pentru articol
                    formatted_item = {'title': title, 'url': link, 'summary': summary, 'timestamp': timestamp, 'source_name': source_display_name}
                    all_news.append(formatted_item); count += 1
            print(f"  Fetched {count} valid items from {source_name}.")
        except Exception as e: print(f"  ERROR parsing feed '{source_name}': {e}") # eroare la parsarea fluxului
        time.sleep(RSS_FETCH_DELAY_FEEDS) # pauza intre preluarea fluxurilor
    print(f"--- Finished RSS fetching. Found {len(all_news)} items. ---")
    return all_news

def get_newsapi_news():
    # preia stiri de la newsapi.org
    if not NEWSAPI_AVAILABLE: return [] # verifica dependenta
    if not NEWSAPI_KEY: print("Error: NEWSAPI_KEY env var not set."); return [] # verifica cheia api
    print("\n--- Fetching news from NewsAPI.org ---")
    all_news = []; processed_links = set() # initializari
    newsapi = NewsApiClient(api_key=NEWSAPI_KEY) # initializeaza clientul newsapi
    # seteaza data de inceput pentru cautare la 2 zile in urma
    from_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')

    for page_num in range(1, NEWSAPI_MAX_PAGES + 1): # itereaza prin pagini
        print(f"  Fetching page {page_num}/{NEWSAPI_MAX_PAGES}...")
        response = None; success = False
        for attempt in range(MAX_RETRIES): # bucla de reincercari
            try:
                # efectueaza cererea catre newsapi
                response = newsapi.get_everything(q=NEWSAPI_QUERY,
                                                  sources=NEWSAPI_SOURCES,
                                                  language=NEWSAPI_LANGUAGE,
                                                  sort_by=NEWSAPI_SORT_BY,
                                                  page_size=NEWSAPI_PAGE_SIZE,
                                                  page=page_num,
                                                  from_param=from_date)
                success = True; break # succes, iesim din bucla de reincercari
            except NewsAPIException as e:
                print(f"  Attempt {attempt+1}/{MAX_RETRIES}: NewsAPI error (Page {page_num}): {e}")
                # daca eroarea este una care indica oprirea (ex. limita atinsa, cheie invalida), oprim preluarea
                if e.get_code() in ['rateLimited', 'maximumResultsReached', 'apiKeyInvalid', 'apiKeyDisabled']:
                    print(f"  {e.get_code()}, stopping NewsAPI fetch."); page_num = NEWSAPI_MAX_PAGES; success=False; break
                if attempt < MAX_RETRIES - 1: time.sleep(RETRY_DELAY * (attempt + 1)) # asteapta exponential
            except Exception as e: # alte exceptii neasteptate
                print(f"  Attempt {attempt+1}/{MAX_RETRIES}: Unexpected NewsAPI error: {e}"); time.sleep(RETRY_DELAY * (attempt + 1))

        if not success or response is None or response.get('status') != 'ok':
            print(f"  Failed NewsAPI page {page_num}. Status: {response.get('status') if response else 'N/A'}"); break # esuat pentru pagina curenta, oprim

        articles = response.get('articles', []) # extrage articolele din raspuns
        if not articles: print(f"  No more articles on NewsAPI page {page_num}."); break # nu mai sunt articole, oprim

        page_added_count = 0
        for article in articles:
            link = article.get('url')
            if link and link not in processed_links: # verifica unicitatea link-ului
                processed_links.add(link)
                timestamp = format_timestamp(article.get('publishedAt')) # formateaza timestamp-ul
                summary = clean_html_summary(article.get('description') or article.get('content')) # curata rezumatul
                title = clean_html_summary(article.get('title', 'N/A')) # curata titlul
                if not title or title == 'N/A': continue # sare peste articol fara titlu

                if summary and len(summary) > 500: summary = summary[:500] + "..." # truncheaza rezumatele lungi

                # creeaza dictionarul formatat
                formatted_item = {
                    'title': title.strip(),
                    'url': link,
                    'summary': summary,
                    'timestamp': timestamp,
                    'source_name': f"NewsAPI ({article.get('source', {}).get('name', 'Unknown')})"
                }
                all_news.append(formatted_item); page_added_count += 1
        print(f"  Added {page_added_count} unique items from NewsAPI page {page_num}.")

        total_results = response.get('totalResults', 0)
        # daca am preluat toate rezultatele disponibile conform estimarii newsapi
        if page_num * NEWSAPI_PAGE_SIZE >= total_results:
            print("  Reached estimated total NewsAPI results."); break
    print(f"--- Finished NewsAPI fetching. Found {len(all_news)} items. ---")
    return all_news

def get_yfinance_news(tickers):
    # preia stiri pentru simbolurile bursiere specificate folosind yfinance
    if not YFINANCE_AVAILABLE: return [] # verifica dependenta
    print(f"\n--- Fetching news from Yahoo Finance (yfinance) for {len(tickers)} tickers ---")
    print("    (Note: yfinance news fetching can be unreliable)")
    all_news = []; processed_links = set() # initializari
    session = requests.Session() if REQUESTS_AVAILABLE else None # foloseste o sesiune requests daca e disponibila
    if session: session.headers.update({'User-Agent': 'Mozilla/5.0'}) # seteaza user-agent pentru sesiune

    for ticker_symbol in tickers:
        print(f"  Fetching news for {ticker_symbol}...")
        news_list = None
        try:
            # initializeaza obiectul ticker yfinance, folosind sesiunea daca exista
            ticker = yf.Ticker(ticker_symbol, session=session) if session else yf.Ticker(ticker_symbol)
            news_list = ticker.news # preia lista de stiri
        except Exception as e:
            print(f"    ERROR getting yfinance .news for {ticker_symbol}: {e}"); time.sleep(0.1); continue # eroare la preluare, treci la urmatorul simbol

        if not news_list: print(f"    No news found via yfinance for {ticker_symbol}."); continue # nu s-au gasit stiri

        count = 0
        for news_item in news_list:
            if not isinstance(news_item, dict): print(f"    Warn: Unexpected yfinance item: {news_item}"); continue # verifica formatul item-ului
            if count >= MAX_ARTICLES_PER_TICKER: break # limiteaza numarul de articole per simbol
            link = news_item.get('link')
            # trateaza link-urile de redirectare de la yahoo (guce.yahoo.com)
            if link and 'guce.yahoo' in link:
                 match = re.search(r'url=([^&]+)', link) # extrage url-ul real
                 if match:
                    try: link = requests.utils.unquote(match.group(1)) # decodeaza url-ul
                    except Exception: link = html.unescape(match.group(1)) # fallback la html.unescape

            if link and link not in processed_links: # verifica unicitatea link-ului
                processed_links.add(link)
                timestamp = format_timestamp(news_item.get('providerPublishTime')) # formateaza timestamp-ul
                title = clean_html_summary(news_item.get('title', 'N/A')) # curata titlul
                publisher = news_item.get('publisher', 'N/A') # obtine publisher-ul
                if not title or title == 'N/A': continue # sare peste articol fara titlu

                # creeaza dictionarul formatat
                formatted_item = {
                    'title': title.strip(),
                    'url': link,
                    'summary': f"Publisher: {publisher}", # rezumat simplu cu publisher-ul
                    'timestamp': timestamp,
                    'related_ticker': ticker_symbol, # adauga simbolul asociat
                    'source_name': 'Yahoo Finance (yfinance)'
                }
                all_news.append(formatted_item); count += 1
        print(f"    Fetched {count} valid items for {ticker_symbol}.")
        time.sleep(REQUEST_DELAY_SOURCES / 3) # pauza intre preluarea simbolurilor
    print(f"--- Finished yfinance fetching. Found {len(all_news)} items. ---")
    return all_news

def get_vix_value_yfinance():
    # preia valoarea curenta (sau recenta) a indicelui vix folosind yfinance
    if not YFINANCE_AVAILABLE: print("Warn: yfinance not available, cannot fetch VIX."); return None
    print("\n--- Fetching VIX Value ---")
    try:
        vix_ticker = yf.Ticker("^VIX") # obiect ticker pentru vix
        hist = vix_ticker.history(period="5d") # preia istoricul pe ultimele 5 zile
        if hist.empty:
            # daca istoricul e gol, incearca sa obtii valoarea din ticker.info
            print("  Warn: History empty, trying ticker.info for VIX.")
            info = vix_ticker.info
            # incearca mai multe campuri posibile pentru pretul de inchidere anterior sau pretul curent
            latest_vix = info.get('regularMarketPreviousClose') or info.get('previousClose') or info.get('regularMarketPrice')
            if latest_vix:
                 print(f"  Fetched VIX from info: {latest_vix:.2f}")
                 return float(latest_vix)
            else:
                print("  ERROR: Could not get VIX from ticker.info either.")
                return None

        latest_vix = hist['Close'].iloc[-1] # ultima valoare de inchidere din istoric
        print(f"  Fetched VIX value (likely previous close): {latest_vix:.2f}")
        return float(latest_vix)
    except Exception as e: print(f"  ERROR fetching VIX value using yfinance: {e}"); return None

# blocul principal de executie
if __name__ == "__main__":
    print("Starting news aggregation and VIX fetching process...")
    start_time = time.time() # marcheaza timpul de inceput
    master_news_list = [] # lista principala pentru toate stirile agregate
    fetched_vix = None # variabila pentru valoarea vix

    # preia valoarea vix
    fetched_vix = get_vix_value_yfinance()

    print(f"\n*** DEBUG: Value of fetched_vix = {fetched_vix} ***\n") # afisare debug

    # preia stirile din rss si le adauga la lista principala
    rss_items = get_rss_news(); master_news_list.extend(rss_items); time.sleep(REQUEST_DELAY_SOURCES)
    # preia stirile din newsapi si le adauga la lista principala
    newsapi_items = get_newsapi_news(); master_news_list.extend(newsapi_items); time.sleep(REQUEST_DELAY_SOURCES)
    # (nota: preluarea stirilor yfinance a fost comentata in codul original, o lasam asa)
    # yfinance_items = get_yfinance_news(YAHOO_TICKERS); master_news_list.extend(yfinance_items)

    print("\n--- Processing Combined Results ---")
    unique_news = [] # lista pentru stirile unice
    print(f"*** DEBUG: Length of master_news_list before processing = {len(master_news_list)} ***") # afisare debug

    if master_news_list: # daca s-au preluat stiri
        print(f"Total fetched before deduplication: {len(master_news_list)}")
        seen_urls = set() # set pentru url-uri vazute (deduplicare)
        invalid_timestamp_count = 0 # contor pentru timestamp-uri invalide

        for i, item in enumerate(master_news_list): # itereaza prin toate stirile
            url = item.get('url')
            if url:
                try:
                    # normalizeaza url-ul pentru o deduplicare mai buna
                    norm_url = url.lower().replace("https://", "").replace("http://", "").replace("www.", "")
                    norm_url = norm_url.split('?')[0].split('#')[0].rstrip('/') # elimina parametrii query, fragmentele si slash-ul final
                    if norm_url and norm_url not in seen_urls: # daca url-ul normalizat e valid si nu a fost vazut
                        ts_str = item.get('timestamp')
                        # verifica validitatea timestamp-ului; daca e invalid, seteaza unul implicit (epoca unix)
                        if not ts_str or not isinstance(ts_str, str) or 'T' not in ts_str:
                             print(f"  Warn #{i+1}: Invalid/missing timestamp '{ts_str}' for URL {url}. Assigning default.")
                             item['timestamp'] = datetime(1970, 1, 1, tzinfo=timezone.utc).isoformat(timespec='seconds') + 'Z' # foloseste .isoformat() si adauga 'z'

                        # adauga articolul la lista unica daca timestamp-ul este un string valid iso
                        if isinstance(item.get('timestamp'), str) and 'T' in item['timestamp']:
                            unique_news.append(item); seen_urls.add(norm_url)
                        else:
                            # articolul este sarit daca timestamp-ul nu a putut fi corectat
                            print(f"  Error #{i+1}: Skipping item with unfixable invalid timestamp format '{item.get('timestamp')}' for URL {url}")
                            invalid_timestamp_count += 1
                except Exception as e: print(f"  Error #{i+1}: Normalizing URL {url}: {e}. Skipping.") # eroare la normalizarea url-ului
        print(f"Total unique articles after deduplication: {len(unique_news)}")
        if invalid_timestamp_count > 0:
            print(f"Skipped {invalid_timestamp_count} items due to invalid timestamp format during processing.")

        try:
            # sorteaza articolele unice dupa timestamp, cele mai noi primele
            unique_news.sort(
                 key=lambda x: datetime.fromisoformat(x['timestamp'].replace('Z', '+00:00')) if isinstance(x.get('timestamp'), str) and 'T' in x['timestamp'] else datetime.min.replace(tzinfo=timezone.utc),
                 reverse=True
            )
            print("Sorted articles by timestamp (newest first).")
        except Exception as sort_e: print(f"Warn: Could not sort articles: {sort_e}.") # avertisment daca sortarea esueaza

        # limiteaza numarul total de articole
        if len(unique_news) > MAX_TOTAL_ARTICLES:
            print(f"Limiting articles from {len(unique_news)} to {MAX_TOTAL_ARTICLES}.")
            unique_news = unique_news[:MAX_TOTAL_ARTICLES]
    else:
        print("\nNo news articles were successfully fetched from any source.") # mesaj daca nu s-au gasit stiri

    # creeaza timestamp-ul pentru valoarea vix
    vix_timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds') + 'Z'
    # structureaza datele de iesire
    output_data = {
        "vix_data": { "vix": fetched_vix, "timestamp_utc": vix_timestamp },
        "articles": unique_news
    }

    print("\n--- Final data to be saved ---")
    print(f"VIX Data: {output_data['vix_data']}")
    print(f"Number of Articles: {len(output_data['articles'])}")
    if output_data['articles']: # afiseaza un exemplu de articol daca exista
        print("Sample Article:", json.dumps(output_data['articles'][0], indent=2))
    print("------------------------------")

    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True) # creeaza directorul de iesire daca nu exista
        output_filepath = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME) # calea completa a fisierului de iesire
        # scrie datele in fisierul json
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False) # indentare pentru lizibilitate, permite caractere non-ascii
        print(f"\nCombined news and VIX data saved to {output_filepath}")

        # verifica daca fisierul a fost creat si afiseaza dimensiunea
        if os.path.exists(output_filepath):
             print(f"File size of {output_filepath}: {os.path.getsize(output_filepath)} bytes.")
        else:
             print(f"ERROR: File {output_filepath} was NOT created.")

    except Exception as e:
        print(f"An error occurred saving combined file to {os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)}: {e}")


    end_time = time.time()
    print(f"\nScript finished in {end_time - start_time:.2f} seconds.")