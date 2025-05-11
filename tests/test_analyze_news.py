import pytest # importa biblioteca pytest pentru a scrie si rula teste
import os # importa modulul os pentru a lucra cu variabile de mediu si cai de fisiere
import json # importa modulul json pentru a lucra cu date json (ex: in fisiere temporare)
from website.crucialPys import analyze_news # importa modulul analyze_news.py pe care vrem sa il testam
from datetime import datetime, timezone # importa clasele datetime si timezone pentru a lucra cu date si ore
from unittest.mock import MagicMock # importa magicmock pentru a crea obiecte simulate (daca nu e injectat de pytest-mock)
import re # importa modulul re pentru expresii regulate (desi nu e folosit direct in acest fisier de test, e folosit in modulul testat)

# teste pentru functia parse_analysis_results
# aceasta functie ar trebui sa extraga indexul fear & greed si textul sumarului dintr-un text mai mare primit de la ai

def test_parse_analysis_results_with_fg():
    """testeaza parsarea cand indexul fear & greed este prezent si exista text dupa el."""
    # definim un text de input simulat, asa cum ar putea veni de la ai
    text_input = ("<think>Some thought process here.</think>\n"
                  "This is the main summary of the market sentiment.\n"
                  "It seems generally positive.\n"
                  "FEAR AND GREED INDEX = 75\n" # linia care contine indexul
                  "Some other text after F&G.")   # text care urmeaza dupa index

    # definim rezultatul pe care ne asteptam sa il obtinem de la functie
    expected = {
        "fear_greed": 75, # valoarea numerica a indexului
        # textul sumarului, curatat de blocul <think> si de linia f&g,
        # dar pastrand textul care era dupa linia f&g
        "summary_text": "This is the main summary of the market sentiment.\nIt seems generally positive.\nSome other text after F&G."
    }
    actual_result = analyze_news.parse_analysis_results(text_input) # apelam functia testata

    # --- print-uri pentru debug (daca testul esueaza, aceste linii vor afisa detalii) ---
    if actual_result != expected:
        print("\n--- DEBUG: test_parse_analysis_results_with_fg ---")
        print(f"ACTUAL   DICT: {repr(actual_result)}")
        print(f"EXPECTED DICT: {repr(expected)}")
        if actual_result.get("summary_text") != expected.get("summary_text"):
            print("--- summary_text MISMATCH ---")
            print(f"ACTUAL   repr(summary_text): {repr(actual_result['summary_text'])}")
            print(f"EXPECTED repr(summary_text): {repr(expected['summary_text'])}")
            print("--- Character by character comparison (first mismatch) ---")
            for i, (c_actual, c_expected) in enumerate(zip(actual_result['summary_text'], expected['summary_text'])):
                if c_actual != c_expected:
                    print(f"Mismatch at index {i}: Actual='{c_actual}' (ord={ord(c_actual)}) vs Expected='{c_expected}' (ord={ord(c_expected)})")
                    break
            else:
                if len(actual_result['summary_text']) != len(expected['summary_text']):
                    print("Strings have different lengths after common part.")
                    print(f"Actual length: {len(actual_result['summary_text'])}, Expected length: {len(expected['summary_text'])}")
                    if len(actual_result['summary_text']) > len(expected['summary_text']):
                        print(f"Extra chars in actual: {repr(actual_result['summary_text'][len(expected['summary_text']):])}")
                    else:
                        print(f"Extra chars in expected: {repr(expected['summary_text'][len(actual_result['summary_text']):])}")
        print(f"--- END DEBUG ---")
    # --- sfarsit print-uri debug ---

    assert actual_result == expected # verificam daca rezultatul actual este egal cu cel asteptat

def test_parse_analysis_results_with_fg_no_trailing_text():
    """testeaza parsarea cand indexul f&g este prezent si este ultimul continut semnificativ."""
    text_input = ("<think>Some thought process here.</think>\n"
                  "This is the main summary of the market sentiment.\n"
                  "It seems generally positive.\n"
                  "FEAR AND GREED INDEX = 75") # linia f&g este la final

    expected = {
        "fear_greed": 75,
        "summary_text": "This is the main summary of the market sentiment.\nIt seems generally positive."
    }
    actual_result = analyze_news.parse_analysis_results(text_input)
    assert actual_result == expected

def test_parse_analysis_results_no_fg():
    """testeaza parsarea cand indexul fear & greed nu este prezent in text."""
    text_input = ("<think>Thinking about it...</think>\n"
                  "The market is quite volatile today, no clear direction.") # nu contine linia f&g
    expected = {
        "fear_greed": None, # ne asteptam ca f&g sa fie none
        "summary_text": "The market is quite volatile today, no clear direction." # sumarul curatat de <think>
    }
    actual_result = analyze_news.parse_analysis_results(text_input)
    assert actual_result == expected

def test_parse_analysis_results_fg_malformed():
    """testeaza parsarea cand linia f&g este malformata (valoarea nu e numerica)."""
    text_input = "Summary. FEAR AND GREED INDEX = XYZ" # xyz nu e un numar
    parsed = analyze_news.parse_analysis_results(text_input) # apelam functia
    assert parsed["fear_greed"] is None # f&g ar trebui sa fie none
    # functia ar trebui sa elimine "fear and greed index = xyz" si sa returneze doar "summary."
    assert parsed["summary_text"] == "Summary."
    # verificam ca textul "fear and greed index" nu mai apare in sumarul rezultat
    assert "FEAR AND GREED INDEX" not in parsed["summary_text"].upper()

def test_parse_analysis_results_empty_input():
    """testeaza parsarea cand textul de input este gol."""
    text_input = ""
    expected = {"fear_greed": None, "summary_text": ""}
    assert analyze_news.parse_analysis_results(text_input) == expected

def test_parse_analysis_results_no_think_block():
    """testeaza parsarea cand textul nu contine blocul <think>...</think>."""
    text_input = ("This is a summary without a think block.\n"
                  "FEAR AND GREED INDEX = 30")
    expected = {
        "fear_greed": 30,
        "summary_text": "This is a summary without a think block."
    }
    assert analyze_news.parse_analysis_results(text_input) == expected

# definim o "fixture" pytest. o fixture este o functie care pregateste date sau configuratii pentru teste.
# 'tmp_path' este o fixture built-in de la pytest care ofera o cale catre un director temporar unic pentru test.
@pytest.fixture
def temp_json_file(tmp_path):
    """creeaza un fisier json temporar pentru a testa functia load_data_from_json."""
    data = { # datele pe care le vom scrie in fisierul json
        "articles": [{"title": "Test Article 1"}],
        "vix_data": {"vix": "20.5"}
    }
    file_path = tmp_path / "test_data.json" # cream calea catre fisierul temporar
    with open(file_path, 'w', encoding='utf-8') as f: # deschidem fisierul pentru scriere
        json.dump(data, f) # scriem datele in format json
    return str(file_path) # returnam calea catre fisierul creat

def test_load_data_from_json_success(temp_json_file): # testul foloseste fixture-ul temp_json_file
    """testeaza incarcarea cu succes a datelor dintr-un fisier json valid."""
    articles, vix = analyze_news.load_data_from_json(temp_json_file) # apelam functia cu fisierul temporar
    assert len(articles) == 1 # verificam daca am incarcat un articol
    assert articles[0]["title"] == "Test Article 1" # verificam continutul articolului
    assert vix == 20.5 # verificam valoarea vix

def test_load_data_from_json_file_not_found():
    """testeaza comportamentul cand fisierul json nu este gasit."""
    articles, vix = analyze_news.load_data_from_json("non_existent_file.json") # incercam sa incarcam un fisier inexistent
    assert articles == [] # ne asteptam la o lista goala de articole
    assert vix is None # ne asteptam ca vix sa fie none

def test_load_data_from_json_invalid_json(tmp_path): # folosim tmp_path pentru a crea un fisier invalid
    """testeaza comportamentul cand fisierul json are continut invalid."""
    file_path = tmp_path / "invalid.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("{not_json_missing_quote ") # scriem continut json invalid
    articles, vix = analyze_news.load_data_from_json(str(file_path)) # incercam sa incarcam
    assert articles == [] # ne asteptam la esec
    assert vix is None

def test_save_results_to_db_success(mocker): # 'mocker' este o fixture de la pytest-mock
    """testeaza salvarea cu succes a rezultatelor in baza de date (simulata)."""
    # simulam (mock-uim) variabilele de mediu pentru credentialele db
    # acest lucru face ca os.environ.get() din analyze_news.py sa returneze aceste valori in timpul testului
    mocker.patch.dict(os.environ, {
        "DB_NAME": "testdb",
        "DB_USER": "user",
        "DB_PASS": "pass",
        "DB_HOST": "localhost" # am adaugat si host pentru completitudine
    })

    mock_conn = mocker.MagicMock() # cream un obiect simulat pentru conexiunea la db
    mock_cursor = mocker.MagicMock() # cream un obiect simulat pentru cursorul db
    # configuram mock_conn astfel incat atunci cand se apeleaza .cursor() si se foloseste cu 'with',
    # sa returneze mock_cursor-ul nostru
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (1,) # simulam ca fetchone() (dupa insert returning id) returneaza id-ul 1

    # inlocuim (patch) apelul real 'psycopg2.connect' din modulul 'analyze_news'
    # cu obiectul nostru simulat 'mock_conn'.
    # cand save_results_to_db va incerca sa faca psycopg2.connect, va primi mock_conn.
    # calea trebuie sa fie exact cea folosita in modulul testat.
    mocker.patch('website.crucialPys.analyze_news.psycopg2.connect', return_value=mock_conn)

    # date de test pentru analiza
    analysis_data = {"fear_greed": 50, "summary_text": "Test summary"}
    vix_value = 20.0
    timestamp = datetime.now(timezone.utc) # timestamp curent in utc

    # apelam functia si verificam daca returneaza true (succes)
    assert analyze_news.save_results_to_db(analysis_data, vix_value, timestamp) is True
    # verificam daca functiile simulate au fost apelate asa cum ne asteptam
    analyze_news.psycopg2.connect.assert_called_once() # verificam daca psycopg2.connect (mock-ul) a fost apelat o data
    mock_cursor.execute.assert_called_once() # verificam daca cursor.execute a fost apelat o data
    mock_conn.commit.assert_called_once() # verificam daca conn.commit a fost apelat o data
    mock_conn.close.assert_called_once() # verificam daca conn.close a fost apelat o data

def test_save_results_to_db_no_credentials(mocker):
    """testeaza comportamentul functiei save_results_to_db cand lipsesc credentialele db."""
    # simulam (mock-uim) variabilele globale db_name, db_user, db_pass din modulul analyze_news
    # ca fiind string-uri goale. acest lucru este necesar daca functia save_results_to_db
    # se bazeaza pe aceste variabile globale definite la incarcarea modulului,
    # si nu doar pe os.environ.get() direct in functie.
    mocker.patch('website.crucialPys.analyze_news.DB_NAME', "")
    mocker.patch('website.crucialPys.analyze_news.DB_USER', "")
    mocker.patch('website.crucialPys.analyze_news.DB_PASS', "")
    # nu mai este nevoie de mocker.patch.dict(os.environ, ...) pentru aceste variabile daca le mock-uim direct in modul

    # date dummy pentru apelul functiei
    dummy_analysis_data = {"fear_greed": 10, "summary_text": "test"}
    dummy_vix = 20.0
    dummy_timestamp = datetime.now(timezone.utc)

    # ne asteptam ca functia sa returneze false deoarece credentialele lipsesc
    assert analyze_news.save_results_to_db(dummy_analysis_data, dummy_vix, dummy_timestamp) is False