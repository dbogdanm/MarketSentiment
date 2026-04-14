import json
from datetime import datetime

def test_index_route_no_data(client, mock_db_cursor):
    mock_db_cursor.fetchone.return_value = None
    mock_db_cursor.fetchall.return_value = []

    response = client.get('/')
    assert response.status_code == 200
    response_data_str = response.data.decode('utf-8')

    assert "Market Sentiment Dashboard" in response_data_str
    assert "No historical data available for the selected period." in response_data_str
    assert "const fearGreedRawValue = '50';" in response_data_str
    assert "const fearGreedData = parseFloat(fearGreedRawValue);" in response_data_str
    assert '<p class="vix-value" id="vixValueDisplay">N/A</p>' in response_data_str
    assert 'Analysis Last Updated: N/A' in response_data_str
    assert 'No AI summary currently available.' in response_data_str

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
    assert "const fearGreedData = parseFloat(fearGreedRawValue);" in html_content
    assert '<p class="vix-value" id="vixValueDisplay">15.50</p>' in html_content
    assert 'Analysis Last Updated: 2023-01-01 12:00:00 UTC' in html_content
    assert "This is a test AI summary from DB." in html_content

    expected_chart_timestamps = json.dumps(["2022-12-30 10:00", "2022-12-31 10:00"])
    assert expected_chart_timestamps in html_content

    expected_chart_fg_values = json.dumps([50, 60])
    assert expected_chart_fg_values in html_content

    expected_chart_vix_values = json.dumps([20.0, 18.2])
    assert expected_chart_vix_values in html_content

    assert '<td>2022-12-31 10:00</td>' in html_content
    assert '<td>60</td>' in html_content
    assert '<td>18.20</td>' in html_content
