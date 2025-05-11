import pytest # importa biblioteca pytest pentru a scrie si rula teste
import requests # importa biblioteca requests, necesara pentru a o putea "mock-ui" (simula) in teste
from website.crucialPys import webScrape # importa modulul webscrape.py pe care vrem sa il testam
from datetime import datetime, timezone # importa clasele datetime si timezone pentru a lucra cu date si ore
import time # importa modulul time pentru functii legate de timp (ex: gmtime, sleep)

# definim niste date de test globale, pe care le vom folosi in testul pentru clean_html_summary
SAMPLE_HTML_SUMMARY = "<p>This is a <b>test</b> summary. & some entities.</p> <!-- comment -->" # un exemplu de text html
EXPECTED_CLEAN_SUMMARY = "This is a test summary. & some entities." # cum ar trebui sa arate textul dupa curatare

def test_clean_html_summary():
    """testeaza functia clean_html_summary din webscrape.py, care curata textul de tag-uri html."""

    # fortam ca flag-ul bs4_available sa fie true pentru acest test,
    # pentru a testa logica ce foloseste beautifulsoup (chiar daca nu e instalat global)
    webScrape.BS4_AVAILABLE = True
    # verificam daca functia curata corect html-ul dat ca exemplu
    assert webScrape.clean_html_summary(SAMPLE_HTML_SUMMARY) == EXPECTED_CLEAN_SUMMARY
    # verificam cum se comporta functia cand primeste none (ar trebui sa returneze "n/a")
    assert webScrape.clean_html_summary(None) == "N/A"
    # verificam cum se comporta cu un string gol
    assert webScrape.clean_html_summary("") == "N/A"
    # verificam cum se comporta cu un string care nu contine html (ar trebui sa ramana la fel)
    assert webScrape.clean_html_summary("No HTML here.") == "No HTML here."

def test_format_timestamp_from_parsed():
    """testeaza functia format_timestamp_from_parsed, care formateaza un obiect 'time.struct_time'."""

    # cream un obiect datetime pentru 1 ianuarie 2023, ora 00:00:00 utc
    dt_obj = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    # convertim obiectul datetime intr-un 'time.struct_time' (un tuplu specific pentru timp)
    # aceasta variabila, parsed_time_struct, nu este folosita direct in asertiunile de mai jos,
    # dar arata cum se poate obtine un astfel de obiect.
    parsed_time_struct = dt_obj.timetuple()

    # cream un alt obiect datetime, nu este folosit direct in asertiuni.
    utc_dt = datetime(2023, 1, 1, 10, 30, 0, tzinfo=timezone.utc)

    # cream un obiect datetime specific pentru testul de formatare: 15 mai 2023, ora 12:00:00 utc
    test_dt = datetime(2023, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    # convertim acest datetime intr-un 'time.struct_time' care reprezinta utc.
    # time.gmtime() converteste un timestamp unix (secunde de la 1 ianuarie 1970) intr-un struct_time utc
    struct_time_utc = time.gmtime(test_dt.timestamp())

    expected_iso = "2023-05-15T12:00:00Z" # formatul iso 8601 pe care il asteptam ca rezultat
    # verificam daca functia formateaza corect struct_time-ul dat
    assert webScrape.format_timestamp_from_parsed(struct_time_utc) == expected_iso
    # verificam cum se comporta functia cand primeste none ca input
    assert webScrape.format_timestamp_from_parsed(None) is None

def test_format_timestamp_various_inputs():
    """testeaza functia format_timestamp cu diverse tipuri de input-uri (string-uri si numere)."""

    # testam cu un string in format iso 8601 cu 'z' la final (care indica utc)
    assert webScrape.format_timestamp("2023-01-01T12:30:00Z") == "2023-01-01T12:30:00Z"

    # testam cu un string care are un offset de fus orar (ex: +02:00)
    # functia ar trebui sa converteasca la utc, deci ora se schimba
    assert webScrape.format_timestamp("2023-01-01T12:30:00+02:00") == "2023-01-01T10:30:00Z"

    # testam cu un string de data si ora fara informatii despre fusul orar
    # functia ar trebui sa presupuna ca este utc sau sa-l converteasca la utc
    assert webScrape.format_timestamp("2023-01-01 12:30:00") == "2023-01-01T12:30:00Z"

    # testam cu un timestamp unix numeric (reprezentand secunde de la 1 ianuarie 1970)
    ts_sec = 1672576200 # aceasta valoare corespunde lui 2023-01-01t12:30:00z
    assert webScrape.format_timestamp(ts_sec) == "2023-01-01T12:30:00Z"

    # testam cu un timestamp unix numeric (reprezentand milisecunde de la 1 ianuarie 1970)
    ts_milli = 1672576200000
    assert webScrape.format_timestamp(ts_milli) == "2023-01-01T12:30:00Z"

    # testam cu un string invalid de data, ne asteptam sa returneze none
    assert webScrape.format_timestamp("invalid-date-string") is None
    # testam cu input none, ne asteptam sa returneze none
    assert webScrape.format_timestamp(None) is None

def test_fetch_url_with_retry_success(mocker): # 'mocker' este o unealta de la pytest-mock pentru a simula (mock-ui) obiecte/functii
    """testeaza cazul de succes al functiei fetch_url_with_retry, cand url-ul este preluat corect."""
    mock_response = mocker.Mock() # cream un obiect simulat (mock) pentru raspunsul http
    mock_response.status_code = 200 # setam codul de status la 200 (care inseamna 'ok')
    mock_response.content = b"Test content" # setam un continut binar simulat pentru raspuns
    mock_response.raise_for_status = mocker.Mock() # simulam functia raise_for_status sa nu faca nimic (pentru ca e un caz de succes)

    # inlocuim (patch) functia 'requests.get' cu obiectul nostru simulat 'mock_response'.
    # cand functia testata (fetch_url_with_retry) va incerca sa apeleze 'requests.get',
    # va apela de fapt obiectul nostru simulat si va primi raspunsul pe care l-am definit noi.
    # calea pentru patch, 'requests.get', presupune ca in webscrape.py se face 'import requests'
    # si apoi se foloseste 'requests.get'. daca s-ar fi facut 'from requests import get',
    # atunci calea pentru patch ar fi fost 'website.crucialpys.webscrape.get'.
    mocker.patch('requests.get', return_value=mock_response)
    webScrape.REQUESTS_AVAILABLE = True # ne asiguram ca flag-ul pentru disponibilitatea bibliotecii requests este true pentru acest test
    content = webScrape.fetch_url_with_retry("http://example.com") # apelam functia pe care o testam
    assert content == b"Test content" # verificam daca am primit continutul asteptat de la mock
    # verificam daca functia simulata 'requests.get' a fost apelata exact o data, cu argumentele corecte
    requests.get.assert_called_once_with("http://example.com", headers=None, timeout=webScrape.REQUEST_TIMEOUT)

def test_fetch_url_with_retry_failure(mocker):
    """testeaza cazul de esec al functiei fetch_url_with_retry, dupa ce toate reincercarile au esuat."""
    # configuram mock-ul pentru 'requests.get' sa ridice o exceptie de tip 'requestsexception'
    # de fiecare data cand este apelat, simuland o eroare de retea persistenta.
    mocker.patch('requests.get', side_effect=requests.exceptions.RequestException("Test error"))
    # simulam functia 'time.sleep' sa nu faca nimic (sa nu astepte efectiv), pentru a accelera testul.
    mocker.patch('time.sleep', return_value=None)
    webScrape.REQUESTS_AVAILABLE = True # asiguram flag-ul
    content = webScrape.fetch_url_with_retry("http://example.com") # apelam functia testata
    assert content is None # ne asteptam ca functia sa returneze none dupa ce toate reincercarile esueaza
    # verificam daca functia simulata 'requests.get' a fost apelata de exact 'webscrape.max_retries' ori.
    assert requests.get.call_count == webScrape.MAX_RETRIES

