import pytest
import os
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock
from website.crucialPys import analyze_news

def test_parse_analysis_results_with_fg():
    text_input = (
        "<think>Some thought process here.</think>\n"
        "This is the main summary of the market sentiment.\n"
        "It seems generally positive.\n"
        "FEAR AND GREED INDEX = 75\n"
        "Some other text after F&G."
    )

    expected = {
        "fear_greed": 75,
        "summary_text": "This is the main summary of the market sentiment.\nIt seems generally positive.\nSome other text after F&G."
    }
    actual_result = analyze_news.parse_analysis_results(text_input)

    if actual_result != expected:
        print("\n--- DEBUG: test_parse_analysis_results_with_fg ---")
        print(f"ACTUAL   DICT: {repr(actual_result)}")
        print(f"EXPECTED DICT: {repr(expected)}")

    assert actual_result == expected

def test_parse_analysis_results_with_fg_no_trailing_text():
    text_input = (
        "<think>Some thought process here.</think>\n"
        "This is the main summary of the market sentiment.\n"
        "It seems generally positive.\n"
        "FEAR AND GREED INDEX = 75"
    )

    expected = {
        "fear_greed": 75,
        "summary_text": "This is the main summary of the market sentiment.\nIt seems generally positive."
    }
    actual_result = analyze_news.parse_analysis_results(text_input)
    assert actual_result == expected

def test_parse_analysis_results_no_fg():
    text_input = (
        "<think>Thinking about it...</think>\n"
        "The market is quite volatile today, no clear direction."
    )
    expected = {
        "fear_greed": None,
        "summary_text": "The market is quite volatile today, no clear direction."
    }
    actual_result = analyze_news.parse_analysis_results(text_input)
    assert actual_result == expected

def test_parse_analysis_results_fg_malformed():
    text_input = "Summary. FEAR AND GREED INDEX = XYZ"
    parsed = analyze_news.parse_analysis_results(text_input)
    assert parsed["fear_greed"] is None
    assert parsed["summary_text"] == "Summary."
    assert "FEAR AND GREED INDEX" not in parsed["summary_text"].upper()

def test_parse_analysis_results_empty_input():
    text_input = ""
    expected = {"fear_greed": None, "summary_text": ""}
    assert analyze_news.parse_analysis_results(text_input) == expected

def test_parse_analysis_results_no_think_block():
    text_input = (
        "This is a summary without a think block.\n"
        "FEAR AND GREED INDEX = 30"
    )
    expected = {
        "fear_greed": 30,
        "summary_text": "This is a summary without a think block."
    }
    assert analyze_news.parse_analysis_results(text_input) == expected

@pytest.fixture
def temp_json_file(tmp_path):
    data = {
        "articles": [{"title": "Test Article 1"}],
        "vix_data": {"vix": "20.5"}
    }
    file_path = tmp_path / "test_data.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return str(file_path)

def test_load_data_from_json_success(temp_json_file):
    articles, vix = analyze_news.load_data_from_json(temp_json_file)
    assert len(articles) == 1
    assert articles[0]["title"] == "Test Article 1"
    assert vix == 20.5

def test_load_data_from_json_file_not_found():
    articles, vix = analyze_news.load_data_from_json("non_existent_file.json")
    assert articles == []
    assert vix is None

def test_load_data_from_json_invalid_json(tmp_path):
    file_path = tmp_path / "invalid.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("{not_json_missing_quote ")
    articles, vix = analyze_news.load_data_from_json(str(file_path))
    assert articles == []
    assert vix is None

def test_save_results_to_db_success(mocker):
    mocker.patch.dict(os.environ, {
        "DB_NAME": "testdb",
        "DB_USER": "user",
        "DB_PASS": "pass",
        "DB_HOST": "localhost"
    })

    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (1,)

    mocker.patch('website.crucialPys.analyze_news.psycopg2.connect', return_value=mock_conn)

    analysis_data = {"fear_greed": 50, "summary_text": "Test summary"}
    vix_value = 20.0
    timestamp = datetime.now(timezone.utc)

    assert analyze_news.save_results_to_db(analysis_data, vix_value, timestamp) is True
    analyze_news.psycopg2.connect.assert_called_once()
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()

def test_save_results_to_db_no_credentials(mocker):
    mocker.patch('website.crucialPys.analyze_news.DB_NAME', "")
    mocker.patch('website.crucialPys.analyze_news.DB_USER', "")
    mocker.patch('website.crucialPys.analyze_news.DB_PASS', "")

    dummy_analysis_data = {"fear_greed": 10, "summary_text": "test"}
    dummy_vix = 20.0
    dummy_timestamp = datetime.now(timezone.utc)

    assert analyze_news.save_results_to_db(dummy_analysis_data, dummy_vix, dummy_timestamp) is False
