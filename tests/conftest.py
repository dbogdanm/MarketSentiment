import os
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Must be set before importing the app: skip DB schema initialization and
# use a deterministic secret key during tests.
os.environ.setdefault("AUTO_INIT_DB", "0")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")

from website import appFlask as flask_app_module  # noqa: E402


@pytest.fixture(scope='module')
def app():
    app_instance = flask_app_module.app
    app_instance.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })
    yield app_instance


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture(autouse=True)
def no_json_cache(monkeypatch):
    # Keep tests deterministic: never pick up a real latest_indices.json
    # produced by previous pipeline runs on this machine.
    monkeypatch.setattr(flask_app_module, "LATEST_JSON_PATH", os.path.join(PROJECT_ROOT, "tests", "_no_such_cache.json"))


@pytest.fixture
def mock_db_cursor(mocker):
    mock_cur = mocker.MagicMock(name="mock_db_cursor_from_fixture")
    mock_conn_obj = mocker.MagicMock(name="mock_db_connection_object")
    mock_conn_obj.cursor.return_value.__enter__.return_value = mock_cur

    mocker.patch('website.appFlask.get_db_connection', return_value=mock_conn_obj)

    return mock_cur
