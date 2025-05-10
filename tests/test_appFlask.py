import json
from datetime import datetime

def test_index_route_no_data(client, mock_db_cursor):
    """Test the index route when the database returns no data."""
    mock_db_cursor.fetchone.return_value = None
    mock_db_cursor.fetchall.return_value = []

    response = client.get('/')
    assert response.status_code == 200
    response_data_str = response.data.decode('utf-8')
    assert "Market Sentiment Dashboard" in response_data_str
    assert "No historical data available yet." in response_data_str
    assert 'const fearGreedData = parseFloat(\'50\');' in response_data_str

def test_index_route_with_data(client, mock_db_cursor):
    """Test the index route when the database returns some data."""
    latest_data_row = {
        "fear_greed": 70,
        "vix": 15.5,
        "timestamp": datetime(2023, 1, 1, 12, 0, 0)
    }
    historical_data_rows = [
        {"fear_greed": 60, "vix": 18.2, "timestamp": datetime(2022, 12, 31, 10, 0, 0)},
        {"fear_greed": 50, "vix": 20.0, "timestamp": datetime(2022, 12, 30, 10, 0, 0)}
    ]

    mock_db_cursor.fetchone.return_value = latest_data_row

    mock_db_cursor.fetchall.return_value = historical_data_rows

    response = client.get('/')
    assert response.status_code == 200
    html_content = response.data.decode('utf-8')

    assert 'const fearGreedData = parseFloat(\'70\');' in html_content
    assert '<p class="vix-value" id="vixValueDisplay">15.50</p>' in html_content
    assert 'Analysis Last Updated: 2023-01-01 12:00:00' in html_content

    expected_chart_timestamps = json.dumps(["2022-12-30 10:00", "2022-12-31 10:00"])
    assert expected_chart_timestamps in html_content

import json
from datetime import datetime

def test_index_route_no_data(client, mock_db_cursor):
    """Test the index route when the database returns no data."""
    mock_db_cursor.fetchone.return_value = None
    mock_db_cursor.fetchall.return_value = []

    response = client.get('/')
    assert response.status_code == 200
    response_data_str = response.data.decode('utf-8')
    assert "Market Sentiment Dashboard" in response_data_str
    assert "No historical data available yet." in response_data_str
    assert 'const fearGreedData = parseFloat(\'50\');' in response_data_str

def test_index_route_with_data(client, mock_db_cursor):
    """Test the index route when the database returns some data."""
    latest_data_row = {
        "fear_greed": 70,
        "vix": 15.5,
        "timestamp": datetime(2023, 1, 1, 12, 0, 0)
    }
    historical_data_rows = [
        {"fear_greed": 60, "vix": 18.2, "timestamp": datetime(2022, 12, 31, 10, 0, 0)},
        {"fear_greed": 50, "vix": 20.0, "timestamp": datetime(2022, 12, 30, 10, 0, 0)}
    ]

    mock_db_cursor.fetchone.return_value = latest_data_row

    mock_db_cursor.fetchall.return_value = historical_data_rows

    response = client.get('/')
    assert response.status_code == 200
    html_content = response.data.decode('utf-8')

    assert 'const fearGreedData = parseFloat(\'70\');' in html_content
    assert '<p class="vix-value" id="vixValueDisplay">15.50</p>' in html_content
    assert 'Analysis Last Updated: 2023-01-01 12:00:00' in html_content

    expected_chart_timestamps = json.dumps(["2022-12-30 10:00", "2022-12-31 10:00"])
    assert expected_chart_timestamps in html_content

