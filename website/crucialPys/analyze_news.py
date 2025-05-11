import os  # pentru a lucra cu caile de fisiere si variabile de mediu
import json  # pentru a lucra cu fisiere si date in format json
import re  # pentru expresii regulate (cautare de text avansata)
import psycopg2  # biblioteca pentru a te conecta si lucra cu baza de date postgresql
from datetime import datetime, timezone  # pentru a lucra cu data si ora, inclusiv fusuri orare
import smtplib
from email.mime.text import MIMEText

# importam clasele necesare din sdk-ul azure pentru a interactiona cu modelul ai
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage  # pentru a structura mesajele trimise la ai
from azure.core.credentials import AzureKeyCredential  # pentru a folosi cheia api la autentificare
from azure.core.exceptions import HttpResponseError  # pentru a prinde erori specifice de la serviciul azure

# --- configuratii pentru cai de fisiere si conexiuni ---
# aflam directorul unde se gaseste acest script (analyze_news.py)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# presupunem ca directorul 'website' este parintele folderului curent (crucialpys)
WEBSITE_DIR = os.path.dirname(SCRIPT_DIR)
# numele fisierului json de unde citim stirile agregate
JSON_FILENAME = "financial_news_agg.json"
# calea completa catre fisierul json cu stiri
JSON_NEWS_FILE_PATH = os.path.join(WEBSITE_DIR, "data_files", JSON_FILENAME)
# directorul unde vom salva fisierul json cu ultimii indici (fear&greed, vix)
INDEX_JSON_OUTPUT_DIR = os.path.join(WEBSITE_DIR, "data_files")
INDEX_JSON_FILENAME = "latest_indices.json"  # numele fisierului pentru ultimii indici
# calea completa pentru fisierul json unde salvam ultimii indici
INDEX_JSON_OUTPUT_PATH = os.path.join(INDEX_JSON_OUTPUT_DIR, INDEX_JSON_FILENAME)

# afisam niste mesaje pentru a sti ce fisiere incearca sa foloseasca scriptul
print(f"Attempting to load data from: {JSON_NEWS_FILE_PATH}")
print(f"Will save latest indices to: {INDEX_JSON_OUTPUT_PATH}")

# luam detaliile de conectare la baza de date din variabilele de mediu ale sistemului
# daca variabila de mediu nu este gasita, se foloseste valoarea default (ex: "localhost")
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
# configuratii pentru serviciul ai (deepseek) de la azure
AZURE_ENDPOINT_URL = "https://deepseekmds7532865580.services.ai.azure.com/models"  # adresa url a modelului tau ai
MODEL_NAME = "DeepSeek-R1-3"  # numele specific al modelului pe care l-ai deployat in azure
AZURE_API_KEY = os.environ.get("AZURE_DEEPSEEK_API_KEY")  # cheia api pentru a accesa serviciul azure

# verificam daca avem cheia api pentru azure; daca nu, afisam un avertisment serios
if not AZURE_API_KEY:
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("!!! CRITICAL WARNING: AZURE_DEEPSEEK_API_KEY not found in environment variables!")
    print("!!! Azure AI API call will fail.")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

# numarul maxim de "cuvinte" (mai exact, tokeni) pe care sa le genereze ai-ul ca raspuns
MAX_TOKENS = 65536  # atentie: aceasta valoare este foarte mare; verifica limita reala a modelului tau specific


def load_data_from_json(filename):
    """incarca articolele de stiri si valoarea vix din fisierul json combinat."""
    articles = []  # initializam o lista goala pentru articole
    vix_value = None  # initializam valoarea vix ca fiind necunoscuta (none)
    print(f"--- Inside load_data_from_json for {filename} ---")  # mesaj de debug
    try:
        # deschidem fisierul json specificat pentru citire ('r')
        # 'encoding="utf-8"' este important pentru a citi corect caracterele speciale (inclusiv diacritice daca ar fi)
        with open(filename, 'r', encoding='utf-8') as f:
            full_data = json.load(f)  # parsam (citim si interpretam) continutul json intr-un dictionar python

        # extragem lista de articole din dictionarul 'full_data'
        # daca cheia "articles" nu exista, .get() va returna o lista goala ([]) ca valoare default
        articles = full_data.get("articles", [])
        print(f"Successfully loaded {len(articles)} news articles key from {filename}.")
        # extragem dictionarul cu datele despre vix
        # daca cheia "vix_data" nu exista, .get() va returna un dictionar gol ({})
        vix_data = full_data.get("vix_data", {})
        vix_value_raw = vix_data.get("vix")  # extragem valoarea vix bruta (poate fi string, numar, sau none)

        if vix_value_raw is not None:  # daca am gasit o valoare pentru vix (nu e none)
            try:
                vix_value = float(vix_value_raw)  # incercam sa o convertim la numar zecimal (float)
                print(f"Loaded VIX value ({vix_value}) from {filename}.")
            except (ValueError, TypeError):  # daca conversia esueaza (ex: vix_value_raw e un text care nu e numar)
                print(f"Warn: Invalid VIX value in {filename}: '{vix_value_raw}'.");
                vix_value = None  # setam vix la none
        else:  # daca cheia "vix" lipseste din vix_data sau valoarea ei este null/none
            print(f"Warn: 'vix' key missing/null in {filename}.");
            vix_value = None
        return articles, vix_value  # returnam lista de articole si valoarea vix

    except FileNotFoundError:  # daca fisierul specificat nu este gasit pe disc
        print(f"Error: Combined JSON not found: {filename}");
        return [], None
    except json.JSONDecodeError as e:  # daca continutul fisierului nu este un json valid
        print(f"Error: Could not decode JSON: {filename}. Error: {e}");
        return [], None
    except Exception as e:  # prindem orice alta eroare neasteptata la incarcarea fisierului
        print(f"Unexpected error loading {filename}: {e}");
        return [], None


def parse_analysis_results(analysis_text):
    """
    parseaza (analizeaza si extrage informatia) textul brut primit de la modelul ai.
    scopul este sa extraga valoarea numerica a indicelui "fear & greed" si textul rezumatului.
    de asemenea, incearca sa elimine din rezumat partea cu "fear and greed index..." si tag-urile "<think>".
    """
    fear_greed = None  # initializam valoarea fear_greed ca necunoscuta
    summary_candidate = analysis_text  # initial, consideram ca tot textul de la ai este un posibil rezumat

    # folosim o expresie regulata (regex) pentru a cauta linia "fear and greed index"
    # urmata optional de ":" sau "=", apoi spatii, si apoi 1 pana la 3 cifre (valoarea indexului).
    # re.ignorecase ignora diferentele de majuscule/minuscule.
    # re.dotall face ca '.' (punctul) din regex sa se potriveasca si cu caracterele newline (\n).
    fg_match = re.search(r"FEAR AND GREED INDEX\s*[:=]?\s*(\d{1,3})", analysis_text, re.IGNORECASE | re.DOTALL)

    if fg_match:  # daca am gasit un tipar care se potriveste (adica am gasit linia f&g cu cifre)
        try:
            fear_greed_value_str = fg_match.group(1)  # extragem doar partea cu cifrele (ex: "75")
            fear_greed = int(fear_greed_value_str)  # convertim cifrele la un numar intreg
            if not (0 <= fear_greed <= 100):  # verificam daca valoarea e in intervalul normal (0-100)
                print(f"Warn: Parsed F&G value {fear_greed} is out of 0-100 range. Setting to None.")
                fear_greed = None  # daca nu e in interval, o consideram invalida
            else:
                print(f"Parsed value - Fear&Greed: {fear_greed}")
        except (ValueError, IndexError) as parse_error:  # daca nu putem converti la intreg sau grupul nu exista
            print(f"Error parsing F&G value from '{fg_match.group(0)}': {parse_error}. F&G=None.")
            fear_greed = None  # setam la none in caz de eroare de parsare a valorii

        # daca am gasit linia f&g, vrem sa o eliminam din textul rezumatului.
        # luam textul de dinainte de inceputul match-ului f&g si il curatam de spatii la sfarsit.
        part_before_fg = analysis_text[:fg_match.start()].rstrip()
        # luam textul de dupa sfarsitul match-ului f&g si il curatam de spatii la inceput.
        part_after_fg = analysis_text[fg_match.end():].lstrip()

        # reconstruim candidatul pentru rezumat.
        # daca avem text si inainte si dupa linia f&g, le unim cu un newline intre ele.
        if part_before_fg and part_after_fg:
            summary_candidate = part_before_fg + "\n" + part_after_fg
        elif part_before_fg:  # daca avem doar text inainte de f&g
            summary_candidate = part_before_fg
        elif part_after_fg:  # daca avem doar text dupa f&g (mai putin probabil)
            summary_candidate = part_after_fg
        else:  # daca ambele parti sunt goale dupa eliminarea f&g
            summary_candidate = ""
    else:  # daca nu am gasit deloc linia f&g in formatul numeric asteptat
        print("Warn: FEAR AND GREED INDEX line with numeric value not found. F&G=None.")
        # incercam sa eliminam orice text care incepe cu "fear and greed index", indiferent ce urmeaza.
        # 'count=1' face ca re.sub sa inlocuiasca doar prima aparitie gasita.
        summary_candidate = re.sub(r"FEAR AND GREED INDEX.*$", "", summary_candidate, count=1,
                                   flags=re.IGNORECASE | re.DOTALL).strip()

    # acum, din summary_candidate (care nu mai contine linia f&g), incercam sa eliminam blocul <think>
    final_summary = summary_candidate
    # cautam tag-ul de inchidere </think> urmat de zero sau mai multe spatii
    think_end_match = re.search(r"</think>\s*", final_summary, re.IGNORECASE | re.DOTALL)

    if think_end_match:  # daca am gasit tag-ul </think>
        # luam doar textul care se afla dupa sfarsitul tag-ului </think> si spatiile aferente
        final_summary = final_summary[think_end_match.end():].strip()
        print("Extracted summary after <think> block.")
    else:  # daca nu exista blocul <think>
        final_summary = final_summary.strip()  # doar curatam spatiile de la capetele textului ramas
        print("Extracted summary (no <think> block found or summary was already clean).")

    return {"fear_greed": fear_greed, "summary_text": final_summary}  # returnam un dictionar cu rezultatele


def analyze_news_with_deepseek(news_articles):
    """trimite lista de articole de stiri la modelul ai deepseek pentru analiza."""
    if not AZURE_API_KEY: print("Error: AZURE_DEEPSEEK_API_KEY env var not set."); return None  # verificam cheia api
    if not news_articles: print("Error: No news articles provided."); return None  # verificam daca avem articole

    # mesajul de sistem care da instructiuni generale modelului ai
    system_message_content = ("...")  # aceasta linie pare redundanta, urmatoarea o suprascrie
    system_message_content = (
        "You are a top financial assistant specialized in analyzing financial news regarding the US stock market. "
        "Your task is to read the provided list of news articles (in JSON format) "
        "and provide a long complex answer covering the overall market sentiment (positive, negative, neutral, mixed), "
        "key events or announcements, and any recurring themes or major concerns mentioned across the articles. "
        "Base your analysis *only* on the information presented in the articles. "
        "Once again, DON'T USE MARKDOWN."  # instructiune clara sa nu foloseasca formatare markdown
        "IMPORTANT: Do  include your thought process or reasoning steps within the main response body and DON'T answer using Markdown."  # spatiu dublu aici la 'do  include', probabil o greseala de tipar
        "When you change the sentence's topic, leave some room before talking about the next topic but don't insert any spaces before the first sentence."  # instructiune pentru spatiere intre paragrafe
        "Write a long-long answer, use as many tokens as possible."  # cerere pentru un raspuns lung
        "Conclude your entire response with a single final line containing ONLY the estimated Fear and Greed value in the following exact format (using capital letters): "
        "\nFEAR AND GREED INDEX = [estimated F&G value]"  # formatul exact pentru linia finala
    )
    try:
        # convertim lista de articole (dictionare python) intr-un string formatat json
        news_json_string = json.dumps(news_articles, indent=2)  # indent=2 pentru lizibilitate
    except TypeError as e:
        print(f"Error encoding news to JSON: {e}");
        return None  # eroare la conversia in json

    # mesajul utilizatorului, care contine instructiunile specifice si datele (articolele json)
    user_message_content = f"You are top financial analyst, please analyze the following news articles and provide the summary and the Fear & Greed index value as instructed.\n\nNews Articles:\n{news_json_string}\n\nAnalysis Summary and Index Value:\n"

    try:
        # initializam clientul pentru a comunica cu serviciul ai de la azure
        client = ChatCompletionsClient(endpoint=AZURE_ENDPOINT_URL, credential=AzureKeyCredential(AZURE_API_KEY))
    except Exception as e:
        print(f"Error initializing Azure Client: {e}");
        return None

    # cream lista de mesaje pentru modelul ai (format de conversatie)
    messages = [
        SystemMessage(content=system_message_content),  # instructiunile de sistem
        UserMessage(content=user_message_content),  # intrebarea/datele de la utilizator
    ]

    print("\n--- Calling Azure DeepSeek R1 API ---")  # mesaj de informare
    print("\n--- Thinking... ---")  # mesaj de informare
    try:
        # facem apelul efectiv la modelul ai pentru a completa conversatia
        response = client.complete(
            messages=messages,  # lista de mesaje
            model=MODEL_NAME,  # numele modelului de folosit
            max_tokens=MAX_TOKENS,  # limita de tokeni pentru raspuns
            temperature=0.5  # controleaza cat de "creativ" e raspunsul (0=foarte factual, 1=foarte creativ)
        )
        print("--- API Call Successful ---")
        # verificam daca am primit un raspuns valid si extragem continutul
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return response.choices[0].message.content  # returnam textul generat de ai
        else:
            print("Error: API response unexpected.", response);
            return None
    except HttpResponseError as e:  # eroare specifica de la serviciul http azure
        print(f"Error during Azure API call: Status {e.status_code}, Reason: {e.reason}");
        return None
    except Exception as e:  # orice alta eroare in timpul apelului api
        print(f"Unexpected error during API call: {e}");
        return None


def save_results_to_db(analysis_data, vix_value, timestamp):
    """salveaza rezultatele analizei in baza de date postgresql."""
    # verificam daca avem credentialele pentru baza de date
    if not all([DB_NAME, DB_USER, DB_PASS]): print("Error: DB credentials missing."); return False
    # verificam daca avem date valide de la analiza ai (in special sumarul)
    if not analysis_data or analysis_data.get("summary_text") is None: print(
        "Error: No valid analysis data for DB."); return False

    conn = None  # initializam variabila pentru conexiune
    inserted = False  # flag pentru a sti daca inserarea a reusit
    try:
        # ne conectam la baza de date folosind credentialele globale
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        print(f"Connected to PostgreSQL DB '{DB_NAME}'.")
        # folosim 'with' pentru cursor, pentru a se inchide automat
        with conn.cursor() as cur:
            # comanda sql pentru a insera un nou rand in tabela sentiment_history
            # '%s' sunt placeholder-e pentru valorile pe care le vom insera (previne sql injection)
            # 'returning id' face ca postgresql sa returneze id-ul randului nou creat
            sql = """INSERT INTO sentiment_history (fear_greed, vix, summary_text, timestamp) VALUES (%s, %s, %s, %s) RETURNING id;"""
            # executam comanda sql cu valorile corespunzatoare
            cur.execute(sql, (
                analysis_data.get("fear_greed"),  # valoarea f&g din dictionarul de analiza
                vix_value,  # valoarea vix
                analysis_data.get("summary_text"),  # textul sumarului din dictionarul de analiza
                timestamp  # timestamp-ul curent
            ))
            inserted_id = cur.fetchone()  # preluam id-ul returnat (va fi un tuplu, ex: (123,))
            conn.commit()  # foarte important: aplicam permanent modificarile in baza de date
            if inserted_id:
                print(f"Successfully inserted DB record ID: {inserted_id[0]}.")
            else:  # in caz ca 'returning id' nu e suportat sau nu returneaza nimic
                print("Successfully inserted DB record (no ID returned).")
            inserted = True  # marcam ca inserarea a reusit
    except (
    Exception, psycopg2.DatabaseError) as error:  # prindem orice eroare legata de baza de date sau alta exceptie
        print(f"Error writing to PostgreSQL DB: {error}")
        if conn:  # daca eroarea a aparut dupa ce conexiunea a fost stabilita
            conn.rollback()  # anulam tranzactia curenta pentru a nu lasa date inconsistente
    finally:  # acest bloc se executa intotdeauna, indiferent daca a fost eroare sau nu
        if conn:  # daca conexiunea a fost creata
            conn.close()  # o inchidem pentru a elibera resursele
            print("Database connection closed.")
    return inserted  # returnam true daca inserarea a reusit, false altfel


def save_indices_to_json(fg_value, vix_value, timestamp, output_path):
    """salveaza cele mai recente valori f&g si vix, impreuna cu timestamp-ul, intr-un fisier json."""
    # cream un dictionar cu datele de salvat
    # formatam timestamp-ul in format iso 8601, cu 'z' la final pentru a indica utc
    index_data = {"fear_greed": fg_value, "vix": vix_value,
                  "timestamp_utc": timestamp.isoformat(timespec='seconds') + 'Z'}

    print(f"--- Data being saved to {output_path} ---")  # mesaj de debug
    print(json.dumps(index_data, indent=2))  # afisam datele formatate frumos
    print("----------------------------------------")

    try:
        # cream directorul de output daca nu exista (os.path.dirname(output_path) ia calea directorului)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        # deschidem fisierul pentru scriere ('w'), cu encoding utf-8
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2)  # scriem datele json, indent=2 pentru formatare lizibila
        print(f"Successfully saved latest indices to {output_path}")
        return True  # returnam true daca salvarea a reusit
    except Exception as e:  # prindem orice eroare la scrierea fisierului
        print(f"An error occurred saving indices JSON to {output_path}: {e}");
        return False


# acest bloc de cod se executa doar atunci cand scriptul este rulat direct
# (de exemplu, cu 'python analyze_news.py'), nu cand este importat ca modul in alt script
if __name__ == "__main__":
    print("Starting news analysis process...")  # mesaj de start
    # initializam variabilele pe care le vom folosi
    analysis_result_text = None  # pentru textul brut de la ai
    parsed_analysis_data = None  # pentru datele parsate (f&g, sumar)
    actual_vix_value = None  # pentru valoarea vix

    # verificam daca fisierul json cu stirile agregate exista
    if not os.path.exists(JSON_NEWS_FILE_PATH):
        print(f"CRITICAL ERROR: Input file {JSON_NEWS_FILE_PATH} does not exist. Run webScrape.py first.")
    else:  # daca fisierul exista
        print(f"Input file {JSON_NEWS_FILE_PATH} found. Proceeding with loading.")
        articles, actual_vix_value = load_data_from_json(JSON_NEWS_FILE_PATH)  # incarcam datele

        # afisam niste informatii de debug despre ce am incarcat
        print(f"*** DEBUG: Loaded articles count = {len(articles) if articles else 0} ***")
        print(f"*** DEBUG: Loaded actual_vix_value = {actual_vix_value} ***")

        if articles:  # daca avem articole de analizat
            analysis_result_text = analyze_news_with_deepseek(articles)  # trimitem la ai pentru analiza
            if analysis_result_text:  # daca am primit un raspuns de la ai
                print("\n--- Raw Analysis Result from API ---");
                print(analysis_result_text);
                print("------------------------------------")
                parsed_analysis_data = parse_analysis_results(analysis_result_text)  # parsam raspunsul

                print(f"*** DEBUG: Parsed analysis data = {parsed_analysis_data} ***")  # afisam datele parsate

                # verificam daca parsarea a avut succes si avem un sumar valid
                if not parsed_analysis_data or not parsed_analysis_data.get("summary_text", "").strip():
                    print("Error: Parsing resulted in empty/invalid summary. Cannot save.");
                    parsed_analysis_data = None  # invalidam datele parsate
                elif parsed_analysis_data.get("fear_greed") is None:  # daca nu am putut parsa f&g
                    print("Warn: Could not parse F&G index.")
            else:  # daca ai-ul nu a returnat nimic
                print("\nAnalysis failed or returned no text.")
        else:  # daca nu am avut articole de la inceput
            print("Could not load news articles. Cannot perform analysis.")

    # afisam un mesaj de debug inainte de a decide daca salvam ceva
    print(
        f"\n*** DEBUG: Check before saving: parsed_analysis_data is {'truthy' if parsed_analysis_data else 'falsy'}, actual_vix_value is {'not None' if actual_vix_value is not None else 'None'} ***")

    # continuam cu salvarea doar daca avem fie date de la analiza ai, fie o valoare vix valida
    if parsed_analysis_data or actual_vix_value is not None:
        # daca analiza ai a esuat (parsed_analysis_data e none), pregatim un dictionar default pentru salvare
        data_for_saving = parsed_analysis_data if parsed_analysis_data else {"fear_greed": None,
                                                                             "summary_text": "News analysis failed or skipped."}

        print("\n--- Final Data (Ready to Save) ---")
        print(f"  Fear & Greed: {data_for_saving.get('fear_greed')}")
        print(f"  VIX: {actual_vix_value}")
        print(
            f"  Summary: {data_for_saving.get('summary_text', '')[:200]}...")  # afisam primele 200 caractere din sumar
        print("-------------------")
        current_analysis_timestamp = datetime.now(timezone.utc)  # luam timestamp-ul curent in utc

        # salvam cele mai recente valori f&g si vix in fisierul json
        json_save_success = save_indices_to_json(
            data_for_saving.get("fear_greed"),
            actual_vix_value,
            current_analysis_timestamp,
            INDEX_JSON_OUTPUT_PATH
        )
        print(f"*** DEBUG: save_indices_to_json returned: {json_save_success} ***")

        # salvam in baza de date doar daca analiza ai a rulat si a produs date parsate valide
        # (adica parsed_analysis_data nu este none)
        if parsed_analysis_data:
            db_save_success = save_results_to_db(
                data_for_saving,
                # folosim data_for_saving care poate avea valori default daca parsarea f&g a esuat, dar sumarul e ok
                actual_vix_value,
                current_analysis_timestamp
            )
            print(f"*** DEBUG: save_results_to_db returned: {db_save_success} ***")
        else:  # daca nu avem date de la ai (parsed_analysis_data e none)
            print("Skipping database save.")
    else:  # daca nu avem nici date de la ai, nici valoare vix
        print("No valid analysis data or VIX value available to save.")

    print("\nAnalysis process finished.")