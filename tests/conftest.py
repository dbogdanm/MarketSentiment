import sys
import os
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from website import appFlask as flask_app_module

@pytest.fixture(scope='module')
def app():
    app_instance = flask_app_module.app
    app_instance.config.update({
        "TESTING": True,
    })
    yield app_instance

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def mock_db_cursor(mocker):
    mock_cur = mocker.MagicMock(name="mock_db_cursor_from_fixture")
    mock_conn_obj = mocker.MagicMock(name="mock_db_connection_object")
    mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cur

    mocker.patch('website.appFlask.get_db_connection', return_value=mock_conn_obj)

    return mock_cur
