import json
from datetime import datetime


def test_index_route_no_data(client, mock_db_cursor):
    mock_db_cursor.fetchone.return_value = None
    mock_db_cursor.fetchall.return_value = []

    response = client.get('/')
    assert response.status_code == 200
    html_content = response.data.decode('utf-8')

    assert "Market Sentiment Dashboard" in html_content
    assert "const fearGreedRawValue = '50';" in html_content
    assert 'id="vixValueDisplay"' in html_content
    assert 'Analysis Last Updated: N/A' in html_content
    assert 'No AI summary currently available.' in html_content
    # No history rows -> empty chart datasets are rendered.
    assert 'const historyTimestamps = [];' in html_content


def test_index_route_with_data(client, mock_db_cursor):
    latest_data_row_mock = {
        "fear_greed": 70,
        "vix": 15.5,
        "timestamp": datetime(2023, 1, 1, 12, 0, 0),
        "summary_text": "This is a test AI summary from DB."
    }

    historical_data_rows_mock = [
        {"id": 2, "fear_greed": 60, "vix": 18.2, "summary_text": "Older summary", "timestamp": datetime(2022, 12, 31, 10, 0, 0)},
        {"id": 1, "fear_greed": 50, "vix": 20.0, "summary_text": "Oldest summary", "timestamp": datetime(2022, 12, 30, 10, 0, 0)}
    ]

    mock_db_cursor.fetchone.return_value = latest_data_row_mock
    mock_db_cursor.fetchall.return_value = historical_data_rows_mock

    response = client.get('/')
    assert response.status_code == 200
    html_content = response.data.decode('utf-8')

    assert "const fearGreedRawValue = '70';" in html_content
    assert '15.50' in html_content
    assert 'Analysis Last Updated: 2023-01-01 12:00:00 UTC' in html_content
    assert "This is a test AI summary from DB." in html_content

    # Chart data is rendered oldest-first.
    assert json.dumps(["2022-12-30 10:00", "2022-12-31 10:00"]) in html_content
    assert json.dumps([50, 60]) in html_content
    assert json.dumps([20.0, 18.2]) in html_content

    # History table shows formatted rows (newest first).
    assert '2022-12-31 10:00' in html_content
    assert '18.20' in html_content
    assert '20.00' in html_content


def test_healthz_db_up(client, mock_db_cursor):
    response = client.get('/healthz')
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["database"] == "up"


def test_healthz_db_down(client, mocker):
    mocker.patch('website.appFlask.get_db_connection', return_value=None)
    response = client.get('/healthz')
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["database"] == "down"


def test_export_csv_no_data(client, mock_db_cursor):
    mock_db_cursor.fetchone.return_value = None
    mock_db_cursor.fetchall.return_value = []

    response = client.get('/export/csv')
    assert response.status_code == 404


def test_export_csv_with_data(client, mock_db_cursor):
    mock_db_cursor.fetchone.return_value = None
    mock_db_cursor.fetchall.return_value = [
        {"id": 1, "fear_greed": 55, "vix": 17.3, "summary_text": "Line one\nLine two", "timestamp": datetime(2023, 1, 2, 9, 30, 0)},
    ]

    response = client.get('/export/csv')
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    body = response.data.decode('utf-8')
    assert "timestamp,fear_greed,vix,summary_text" in body
    assert "2023-01-02 09:30:00 UTC" in body
    # Newlines inside summaries are flattened so each record stays on one CSV row.
    assert "Line one Line two" in body


def test_run_script_busy_returns_409(client, mocker):
    import website.appFlask as app_module
    acquired = app_module._script_lock.acquire(blocking=False)
    assert acquired
    try:
        response = client.post('/run_webscrape')
        assert response.status_code == 409
        assert response.get_json()["status"] == "error"
    finally:
        app_module._script_lock.release()
