import pytest
import os
import json
from website.crucialPys import analyze_news
from datetime import datetime, timezone

def test_parse_analysis_results_with_fg():
    """Test parsing when Fear & Greed index is present."""
    text = """<think>Some thought process here.</think>
    This is the main summary of the market sentiment.
    It seems generally positive.
    FEAR AND GREED INDEX = 75
    Some other text after F&G.
    """
    expected = {"fear_greed": 75, "summary_text": "This is the main summary of the market sentiment.\nIt seems generally positive."}
    assert analyze_news.parse_analysis_results(text) == expected

def test_parse_analysis_results_no_fg():
    """Test parsing when Fear & Greed index is NOT present."""
    text = """<think>Thinking about it...</think>
    The market is quite volatile today, no clear direction.
    """
    expected = {"fear_greed": None, "summary_text": "The market is quite volatile today, no clear direction."}
    assert analyze_news.parse_analysis_results(text) == expected

def test_parse_analysis_results_fg_malformed():
    """Test parsing when F&G line is malformed."""
    text = "Summary. FEAR AND GREED INDEX = XYZ"

    parsed = analyze_news.parse_analysis_results(text)
    assert parsed["fear_greed"] is None
    assert "Summary" in parsed["summary_text"]
    assert "FEAR AND GREED INDEX" not in parsed["summary_text"].upper()

def test_parse_analysis_results_empty_input():
    text = ""
    expected = {"fear_greed": None, "summary_text": ""}
    assert analyze_news.parse_analysis_results(text) == expected

def test_parse_analysis_results_no_think_block():
    text = "This is a summary without a think block. FEAR AND GREED INDEX = 30"
    expected = {"fear_greed": 30, "summary_text": "This is a summary without a think block."}
    assert analyze_news.parse_analysis_results(text) == expected

@pytest.fixture
def temp_json_file(tmp_path):
    """Creates a temporary JSON file for testing load_data_from_json."""
    data = {
        "articles": [{"title": "Test Article 1"}],
        "vix_data": {"vix": "20.5"}
    }
    file_path = tmp_path / "test_data.json"
    with open(file_path, 'w') as f:
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
    with open(file_path, 'w') as f:
        f.write("{not_json: ")
    articles, vix = analyze_news.load_data_from_json(str(file_path))
    assert articles == []
    assert vix is None

def test_save_results_to_db_success(mocker):
    """Test successful save to DB."""

    mocker.patch.dict(os.environ, {"DB_NAME": "testdb", "DB_USER": "user", "DB_PASS": "pass"})

    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (1,)

    mocker.patch('psycopg2.connect', return_value=mock_conn)

    analysis_data = {"fear_greed": 50, "summary_text": "Test summary"}
    vix_value = 20.0
    timestamp = datetime.now(timezone.utc)

    assert analyze_news.save_results_to_db(analysis_data, vix_value, timestamp) is True
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()

def test_save_results_to_db_no_credentials(mocker):

    mocker.patch.dict(os.environ, {"DB_NAME": "", "DB_USER": "", "DB_PASS": ""})

import pytest
import os
import json
from website.crucialPys import analyze_news
from datetime import datetime, timezone

def test_parse_analysis_results_with_fg():
    """Test parsing when Fear & Greed index is present."""
    text = """<think>Some thought process here.</think>
    This is the main summary of the market sentiment.
    It seems generally positive.
    FEAR AND GREED INDEX = 75
    Some other text after F&G.
    """
    expected = {"fear_greed": 75, "summary_text": "This is the main summary of the market sentiment.\nIt seems generally positive."}
    assert analyze_news.parse_analysis_results(text) == expected

def test_parse_analysis_results_no_fg():
    """Test parsing when Fear & Greed index is NOT present."""
    text = """<think>Thinking about it...</think>
    The market is quite volatile today, no clear direction.
    """
    expected = {"fear_greed": None, "summary_text": "The market is quite volatile today, no clear direction."}
    assert analyze_news.parse_analysis_results(text) == expected

def test_parse_analysis_results_fg_malformed():
    """Test parsing when F&G line is malformed."""
    text = "Summary. FEAR AND GREED INDEX = XYZ"

    parsed = analyze_news.parse_analysis_results(text)
    assert parsed["fear_greed"] is None
    assert "Summary" in parsed["summary_text"]
    assert "FEAR AND GREED INDEX" not in parsed["summary_text"].upper()

def test_parse_analysis_results_empty_input():
    text = ""
    expected = {"fear_greed": None, "summary_text": ""}
    assert analyze_news.parse_analysis_results(text) == expected

def test_parse_analysis_results_no_think_block():
    text = "This is a summary without a think block. FEAR AND GREED INDEX = 30"
    expected = {"fear_greed": 30, "summary_text": "This is a summary without a think block."}
    assert analyze_news.parse_analysis_results(text) == expected

@pytest.fixture
def temp_json_file(tmp_path):
    """Creates a temporary JSON file for testing load_data_from_json."""
    data = {
        "articles": [{"title": "Test Article 1"}],
        "vix_data": {"vix": "20.5"}
    }
    file_path = tmp_path / "test_data.json"
    with open(file_path, 'w') as f:
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
    with open(file_path, 'w') as f:
        f.write("{not_json: ")
    articles, vix = analyze_news.load_data_from_json(str(file_path))
    assert articles == []
    assert vix is None

def test_save_results_to_db_success(mocker):
    """Test successful save to DB."""

    mocker.patch.dict(os.environ, {"DB_NAME": "testdb", "DB_USER": "user", "DB_PASS": "pass"})

    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (1,)

    mocker.patch('psycopg2.connect', return_value=mock_conn)

    analysis_data = {"fear_greed": 50, "summary_text": "Test summary"}
    vix_value = 20.0
    timestamp = datetime.now(timezone.utc)

    assert analyze_news.save_results_to_db(analysis_data, vix_value, timestamp) is True
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()

def test_save_results_to_db_no_credentials(mocker):

    mocker.patch.dict(os.environ, {"DB_NAME": "", "DB_USER": "", "DB_PASS": ""})
    assert analyze_news.save_results_to_db({}, None, None) is False