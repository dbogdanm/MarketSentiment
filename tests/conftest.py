import sys # importa modulul sys pentru a lucra cu sistemul (ex: sys.path)
import os # importa modulul os pentru a lucra cu cai de fisiere si sistemul de operare

# calculam calea absoluta catre directorul radacina al proiectului.
# os.path.dirname(__file__) ne da calea catre directorul unde se afla acest fisier (adica 'tests/').
# os.path.join(..., '..') urca un nivel in structura de directoare, ajungand la radacina proiectului.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# adaugam directorul radacina al proiectului la sys.path (lista de locuri unde python cauta module).
# acest lucru este important pentru ca testele sa poata importa corect modulele din proiectul nostru
# (ex: 'from website import appflask').
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT) # il inseram la inceputul listei pentru prioritate

import pytest # importa biblioteca pytest
# importam modulul appflask din pachetul website.
# 'flask_app_module' este un alias pentru a evita posibile conflicte de nume cu fixtures pytest.
# aceasta linie trebuie sa functioneze dupa ce am adaugat project_root la sys.path.
from website import appFlask as flask_app_module


# definim o fixture numita 'app'.
# '@pytest.fixture' este un decorator care marcheaza functia ca fiind o fixture.
# 'scope="module"' inseamna ca aceasta fixture va fi creata o singura data pentru fiecare fisier de test (modul)
# care o foloseste, nu pentru fiecare functie de test individuala.
@pytest.fixture(scope='module')
def app():
    """creeaza si configureaza o instanta a aplicatiei flask pentru a fi folosita in teste."""
    app_instance = flask_app_module.app # luam instanta 'app' din modulul nostru appflask.py
    # actualizam configuratia aplicatiei pentru a o seta in modul de testare.
    # 'testing = true' dezactiveaza anumite comportamente specifice productiei (ex: error handling diferit).
    app_instance.config.update({
        "TESTING": True,
        # aici poti adauga orice alte configurari specifice pentru teste,
        # de exemplu, o baza de date de test in memorie, daca ai folosi sqlalchemy.
    })
    # 'yield' este similar cu 'return', dar permite si executarea unui cod de curatare dupa ce testele au folosit fixture-a.
    # in acest caz, doar returnam instanta aplicatiei.
    yield app_instance
    # aici s-ar putea adauga cod de curatare dupa ce toate testele din modul s-au terminat, daca ar fi necesar.


# definim o fixture numita 'client'.
# aceasta fixture depinde de fixture-a 'app' (o primeste ca argument).
# scope-ul implicit este 'function', deci se va crea un client nou pentru fiecare functie de test.
@pytest.fixture()
def client(app):
    """creeaza un client de test pentru aplicatia flask.
    acest client permite simularea cererilor http (get, post, etc.) catre aplicatie
    fara a fi nevoie sa pornim un server web real.
    """
    return app.test_client() # returnam clientul de test asociat cu instanta 'app'.


# definim o fixture numita 'runner'.
# aceasta depinde de fixture-a 'app'.
@pytest.fixture
def runner(app):
    """un 'runner' pentru a testa comenzi cli (command line interface) definite in flask,
    daca ai avea comenzi custom (ex: pentru a initializa baza de date).
    """
    return app.test_cli_runner() # returnam runner-ul de comenzi cli.


# definim o fixture numita 'mock_db_cursor'.
# aceasta depinde de fixture-a 'mocker' (furnizata de plugin-ul pytest-mock).
@pytest.fixture
def mock_db_cursor(mocker):  # 'mocker' este unealta pentru a crea obiecte simulate (mocks)
    """
    simuleaza (mock-uieste) conexiunea la baza de date si cursorul.
    scopul este de a preveni interactiunile reale cu baza de date in timpul testelor,
    facand testele mai rapide, izolate si predictibile.
    """
    # cream un obiect simulat (mock) pentru cursorul bazei de date.
    # 'name' este util pentru debugging, apare in mesajele de eroare daca mock-ul nu e folosit corect.
    mock_cur = mocker.MagicMock(name="mock_db_cursor_from_fixture")
    # cream un obiect simulat pentru conexiunea la baza de date.
    mock_conn_obj = mocker.MagicMock(name="mock_db_connection_object")

    # configuram obiectul simulat de conexiune.
    # cand se apeleaza metoda '.cursor()' pe mock_conn_obj, vrem sa returneze un obiect
    # care, atunci cand este folosit intr-un context 'with ... as ...:', sa returneze mock_cur-ul nostru.
    # '__enter__' si '__exit__' sunt metode speciale pentru context managers ('with' statement).
    mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cur

    # inlocuim (patch) functia reala 'get_db_connection' din modulul 'website.appflask'
    # cu obiectul nostru simulat 'mock_conn_obj'.
    # cand codul din appflask.py va apela 'get_db_connection()', va primi de fapt mock_conn_obj.
    mocker.patch('website.appFlask.get_db_connection', return_value=mock_conn_obj)

    # fixture-a returneaza cursorul simulat, astfel incat testele sa poata configura
    # ce metode ale cursorului (ex: fetchone, fetchall) sa returneze.
    return mock_cur