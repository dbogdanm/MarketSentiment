import json # importa biblioteca json pentru a lucra cu string-uri json (ex: pentru datele graficelor)
from datetime import datetime # importa clasa datetime pentru a crea obiecte de data si ora pentru test

# fixtures 'client' si 'mock_db_cursor' sunt definite in fisierul conftest.py
# si sunt injectate automat de pytest in functiile de test care le declara ca argumente.

def test_index_route_no_data(client, mock_db_cursor):
    """
    testeaza ruta principala ('/') a aplicatiei flask in cazul in care baza de date
    nu returneaza nicio data (nici date recente, nici istoric).
    'client' este un client de test flask care simuleaza un browser.
    'mock_db_cursor' este un obiect simulat (mock) pentru cursorul bazei de date.
    """
    # configuram mock-ul pentru cursor sa returneze none cand se cere ultimul rand (fetchone)
    mock_db_cursor.fetchone.return_value = None
    # configuram mock-ul sa returneze o lista goala cand se cere istoricul (fetchall)
    mock_db_cursor.fetchall.return_value = []

    response = client.get('/') # facem un request http get catre ruta principala
    assert response.status_code == 200 # verificam daca raspunsul http are statusul 200 (ok)
    response_data_str = response.data.decode('utf-8') # decodam continutul raspunsului (html-ul paginii)

    # verificam daca anumite texte cheie sunt prezente in html-ul paginii
    assert "Market Sentiment Dashboard" in response_data_str # titlul principal
    assert "No historical data available for the selected period." in response_data_str # mesajul pentru tabel gol
    # verificam cum sunt injectate datele default in javascript-ul din pagina
    assert "const fearGreedRawValue = '50';" in response_data_str # valoarea default pentru f&g
    assert "const fearGreedData = parseFloat(fearGreedRawValue);" in response_data_str # linia de parsare js
    assert '<p class="vix-value" id="vixValueDisplay">N/A</p>' in response_data_str # valoarea default pentru vix
    assert 'Analysis Last Updated: N/A' in response_data_str # data ultimei actualizari default
    assert 'No AI summary currently available.' in response_data_str # sumarul ai default

def test_index_route_with_data(client, mock_db_cursor):
    """
    testeaza ruta principala ('/') a aplicatiei flask in cazul in care baza de date
    returneaza date (atat date recente, cat si istoric).
    """
    # definim date simulate pe care ne asteptam ca baza de date (mock-uita) sa le returneze
    # pentru cea mai recenta inregistrare
    latest_data_row_mock = {
        "fear_greed": 70,
        "vix": 15.5,
        "timestamp": datetime(2023, 1, 1, 12, 0, 0), # un obiect datetime fara fus orar
        "summary_text": "This is a test AI summary from DB."
    }
    # pentru istoricul de date (presupunem ca vin sortate descrescator dupa timp din db)
    historical_data_rows_mock = [
        {"id": 2, "fear_greed": 60, "vix": 18.2, "summary_text": "Older summary", "timestamp": datetime(2022, 12, 31, 10, 0, 0)},
        {"id": 1, "fear_greed": 50, "vix": 20.0, "summary_text": "Oldest summary", "timestamp": datetime(2022, 12, 30, 10, 0, 0)}
    ]

    # configuram mock-ul pentru cursor sa returneze datele noastre simulate
    mock_db_cursor.fetchone.return_value = latest_data_row_mock
    mock_db_cursor.fetchall.return_value = historical_data_rows_mock

    response = client.get('/') # facem request-ul get
    assert response.status_code == 200 # verificam statusul
    html_content = response.data.decode('utf-8') # luam continutul html

    # verificam daca valorile recente sunt corect afisate sau injectate in javascript
    assert "const fearGreedRawValue = '70';" in html_content
    assert "const fearGreedData = parseFloat(fearGreedRawValue);" in html_content
    assert '<p class="vix-value" id="vixValueDisplay">15.50</p>' in html_content
    # functia din appflask.py formateaza timestamp-ul fara fus orar adaugand " utc" la final
    assert 'Analysis Last Updated: 2023-01-01 12:00:00 UTC' in html_content
    assert "This is a test AI summary from DB." in html_content # verificam sumarul ai

    # verificam datele pentru grafice (chart)
    # functia get_sentiment_data_from_db inverseaza ordinea pentru grafice (cel mai vechi primul)
    # si formateaza timestamp-urile ca 'aaaa-ll-zz hh:mm'
    expected_chart_timestamps = json.dumps(["2022-12-30 10:00", "2022-12-31 10:00"])
    assert expected_chart_timestamps in html_content

    expected_chart_fg_values = json.dumps([50, 60]) # valorile f&g in ordinea pentru grafic
    assert expected_chart_fg_values in html_content

    expected_chart_vix_values = json.dumps([20.0, 18.2]) # valorile vix in ordinea pentru grafic
    assert expected_chart_vix_values in html_content

    # verificam un rand din tabelul istoric (tabelul afiseaza cele mai noi primele)
    # deci primul rand din tabel ar trebui sa corespunda cu historical_data_rows_mock[0]
    assert '<td>2022-12-31 10:00</td>' in html_content # timestamp formatat pentru tabel
    assert '<td>60</td>' in html_content # valoarea f&g
    assert '<td>18.20</td>' in html_content # valoarea vix formatata