# tests/test_analyze_news.py
import pytest
import os
import json
from website.crucialPys import analyze_news
from datetime import datetime, timezone

# Asigură-te că fișierul de test are acces la variabilele de configurare
# sau le mock-uiești. Pentru simplitate, aici vom presupune că sunt setate
# sau nu sunt critice pentru funcțiile testate unitar.

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
    # Actual behavior is to not find the regex, so F&G is None and summary is the whole text minus F&G line attempt
    parsed = analyze_news.parse_analysis_results(text)
    assert parsed["fear_greed"] is None
    assert "Summary" in parsed["summary_text"] # Specifics depend on regex removal logic
    assert "FEAR AND GREED INDEX" not in parsed["summary_text"].upper() # Check if it was removed

def test_parse_analysis_results_empty_input():
    text = ""
    expected = {"fear_greed": None, "summary_text": ""}
    assert analyze_news.parse_analysis_results(text) == expected

def test_parse_analysis_results_no_think_block():
    text = "This is a summary without a think block. FEAR AND GREED INDEX = 30"
    expected = {"fear_greed": 30, "summary_text": "This is a summary without a think block."}
    assert analyze_news.parse_analysis_results(text) == expected

# Test pentru load_data_from_json (necesită un fișier JSON temporar)
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
        f.write("{not_json: ") # Invalid JSON
    articles, vix = analyze_news.load_data_from_json(str(file_path))
    assert articles == []
    assert vix is None

# Testarea analyze_news_with_deepseek și save_results_to_db ar necesita
# mock-uirea extensivă a clientului Azure AI și a conexiunii psycopg2.
# Exemplu schematic pentru save_results_to_db:
def test_save_results_to_db_success(mocker):
    """Test successful save to DB."""
    # Mock environment variables for DB
    mocker.patch.dict(os.environ, {"DB_NAME": "testdb", "DB_USER": "user", "DB_PASS": "pass"})

    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor # For 'with ... as cur:'
    mock_cursor.fetchone.return_value = (1,) # Simulate returning an ID

    mocker.patch('psycopg2.connect', return_value=mock_conn)

    analysis_data = {"fear_greed": 50, "summary_text": "Test summary"}
    vix_value = 20.0
    timestamp = datetime.now(timezone.utc)

    assert analyze_news.save_results_to_db(analysis_data, vix_value, timestamp) is True
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()

def test_save_results_to_db_no_credentials(mocker):
    # Ensure no DB creds are set for this test
    mocker.patch.dict(os.environ, {"DB_NAME": "", "DB_USER": "", "DB_PASS": ""})
    assert analyze_news.save_results_to_db({}, None, None) is False