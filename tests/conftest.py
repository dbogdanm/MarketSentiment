# tests/conftest.py
import sys
import os

# --- MODIFICARE SYS.PATH (TREBUIE SĂ FIE LA ÎNCEPUT) ---
# Calculează calea către directorul rădăcină al proiectului
# __file__ este calea absolută către acest fișier (conftest.py)
# os.path.dirname(__file__) este directorul 'tests/'
# os.path.join(os.path.dirname(__file__), '..') urcă un nivel la rădăcina proiectului
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Adaugă rădăcina proiectului la sys.path dacă nu este deja acolo
# Acest lucru permite importuri de genul 'from website import ...'
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# --- SFÂRȘITUL MODIFICĂRII SYS.PATH ---

# Acum putem importa modulele necesare
import pytest
# Importă modulul aplicației Flask DUPĂ ce sys.path a fost modificat
from website import appFlask as flask_app_module

@pytest.fixture(scope='module')
def app():
    """
    Creează și configurează o instanță a aplicației Flask pentru teste.
    'scope="module"' înseamnă că această fixture va rula o singură dată per modul de test.
    """
    app_instance = flask_app_module.app # Accesează instanța 'app' din modulul tău appFlask
    app_instance.config.update({
        "TESTING": True,
        # Alte configurări specifice testelor, dacă sunt necesare
        # De exemplu, o bază de date de test:
        # "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })

    # Aici poți face și alte setări dacă este necesar,
    # cum ar fi crearea contextului aplicației.
    # with app_instance.app_context():
    #     # Inițializare DB de test etc.
    #     pass

    yield app_instance # Furnizează instanța aplicației testelor

    # Aici poți adăuga cod de curățare dacă este necesar,
    # care va rula după ce toate testele din modul s-au terminat.

@pytest.fixture() # Scope-ul implicit este 'function', rulează pentru fiecare funcție de test
def client(app):
    """
    Creează un client de test pentru aplicația Flask.
    Acesta permite simularea cererilor HTTP către aplicație fără a rula un server web real.
    """
    return app.test_client()

@pytest.fixture
def runner(app):
    """
    Un runner pentru comenzi CLI Flask, dacă ai comenzi custom.
    """
    return app.test_cli_runner()

@pytest.fixture
def mock_db_cursor(mocker): # 'mocker' este o fixture de la pytest-mock
    """
    Mock-uiește conexiunea la baza de date și cursorul.
    Previne interacțiunile reale cu baza de date în timpul testelor unitare/de integrare.
    """
    mock_cur = mocker.MagicMock(name="mock_db_cursor_from_fixture")
    mock_conn_obj = mocker.MagicMock(name="mock_db_connection_object")

    # Configurează mock-ul pentru a funcționa cu 'with ... as cur:'
    mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cur

    # Mock-uiește funcția 'get_db_connection' din modulul 'website.appFlask'
    # Important: calea către funcția mock-uită trebuie să fie exactă.
    mocker.patch('website.appFlask.get_db_connection', return_value=mock_conn_obj)

    return mock_cur # Testele vor putea configura acest mock_cur (ex. ce returnează fetchone)