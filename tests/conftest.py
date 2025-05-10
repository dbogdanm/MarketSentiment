import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest

from website import appFlask as flask_app_module

@pytest.fixture(scope='module')
def app():
    """
    Creeaza si configureaza o instanta pt flask
    """
    app_instance = flask_app_module.app
    app_instance.config.update({
        "TESTING": True,

    })

    yield app_instance

@pytest.fixture()
def client(app):
    """
    Creeaza un client de test pentru flask
    Acesta permite simularea cererilor HTTP catre aplicație fara a rula un server web real
    """
    return app.test_client()

@pytest.fixture
def runner(app):
    """
    Un runner pentru comenzi CLI Flask, daca exista comenzi custom
    """
    return app.test_cli_runner()

@pytest.fixture
def mock_db_cursor(mocker):
    """
    Mock-uiește conexiunea la baza de date
    Previne interactiunile reale cu baza de date in timpul testelor unitare/de integrare
    """
    mock_cur = mocker.MagicMock(name="mock_db_cursor_from_fixture")
    mock_conn_obj = mocker.MagicMock(name="mock_db_connection_object")

    mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cur

    mocker.patch('website.appFlask.get_db_connection', return_value=mock_conn_obj)



import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest

from website import appFlask as flask_app_module

@pytest.fixture(scope='module')
def app():
    """
    Creeaza și configureaza o instanta flask
    """
    app_instance = flask_app_module.app
    app_instance.config.update({
        "TESTING": True,

    })

    yield app_instance

@pytest.fixture()
def client(app):
    """
    Creeaza un client de test pentru aplicația Flask
    Acesta permite simularea cererilor HTTP către aplicatie fara sa ruleze un server web real
    """
    return app.test_client()

@pytest.fixture
def runner(app):
    """
    Un runner pentru comenzi CLI Flask
    """
    return app.test_cli_runner()

@pytest.fixture
def mock_db_cursor(mocker):
    """
    Mock-uieste conexiunea la baza de date si cursorul
    Previne interactiunile reale cu baza de date în timpul testelor unitare/de integrare
    """
    mock_cur = mocker.MagicMock(name="mock_db_cursor_from_fixture")
    mock_conn_obj = mocker.MagicMock(name="mock_db_connection_object")

    mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cur

    mocker.patch('website.appFlask.get_db_connection', return_value=mock_conn_obj)

    return mock_cur