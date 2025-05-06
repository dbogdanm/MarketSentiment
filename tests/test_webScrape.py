# tests/test_webScrape.py
import pytest
import requests
from website.crucialPys import webScrape # Asigură-te că importul funcționează
from datetime import datetime, timezone
import time

# Mock data if necessary, for example, mock HTML content for clean_html_summary
SAMPLE_HTML_SUMMARY = "<p>This is a <b>test</b> summary. & some entities.</p> <!-- comment -->"
EXPECTED_CLEAN_SUMMARY = "This is a test summary. & some entities."

def test_clean_html_summary():
    """Test the HTML cleaning function."""
    # Test with BS4 available (assuming it is for the main run)
    webScrape.BS4_AVAILABLE = True # Force for test if needed
    assert webScrape.clean_html_summary(SAMPLE_HTML_SUMMARY) == EXPECTED_CLEAN_SUMMARY
    assert webScrape.clean_html_summary(None) == "N/A"
    assert webScrape.clean_html_summary("") == "N/A"
    assert webScrape.clean_html_summary("No HTML here.") == "No HTML here."

def test_format_timestamp_from_parsed():
    """Test formatting timestamp from time.struct_time."""
    # Create a sample time.struct_time (e.g., for Jan 1, 2023, 00:00:00 UTC)
    # Note: time.mktime uses local timezone, so careful conversion might be needed
    # For simplicity, let's assume a specific timestamp
    dt_obj = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    parsed_time_struct = dt_obj.timetuple() # This is already UTC-aware due to dt_obj

    # To correctly test mktime behavior, we need to consider its local time assumption
    # A more robust way to get a struct_time for UTC:
    utc_dt = datetime(2023, 1, 1, 10, 30, 0, tzinfo=timezone.utc)
    # Forcing a specific struct_time without relying on local mktime subtleties for this test
    # time.struct_time(tm_year=2023, tm_mon=1, tm_mday=1, tm_hour=10, tm_min=30, tm_sec=0, tm_wday=6, tm_yday=1, tm_isdst=0)
    # For simplicity, we'll test with a known output.
    # Let's construct a struct_time that corresponds to a known ISO string
    # Example: 2023-01-01T10:30:00Z
    # This is tricky because mktime is local.
    # Let's test the direct conversion logic
    test_dt = datetime(2023, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    # Convert to struct_time as it would be parsed by feedparser (often naive then assumed UTC)
    # feedparser.parse results in time.struct_time that represents UTC
    struct_time_utc = time.gmtime(test_dt.timestamp())

    expected_iso = "2023-05-15T12:00:00Z"
    assert webScrape.format_timestamp_from_parsed(struct_time_utc) == expected_iso
    assert webScrape.format_timestamp_from_parsed(None) is None

def test_format_timestamp_various_inputs():
    """Test formatting timestamp from various string and numeric inputs."""
    # Test ISO string
    assert webScrape.format_timestamp("2023-01-01T12:30:00Z") == "2023-01-01T12:30:00Z"
    # Test string with timezone offset
    assert webScrape.format_timestamp("2023-01-01T12:30:00+02:00") == "2023-01-01T10:30:00Z"
    # Test string without timezone (should assume UTC or be converted)
    # The function's logic: if dt.tzinfo is None... dt = dt.replace(tzinfo=timezone.utc)
    assert webScrape.format_timestamp("2023-01-01 12:30:00") == "2023-01-01T12:30:00Z"
    # Test numeric timestamp (seconds)
    ts_sec = 1672576200 # Corresponds to 2023-01-01T12:30:00Z
    assert webScrape.format_timestamp(ts_sec) == "2023-01-01T12:30:00Z"
    # Test numeric timestamp (milliseconds)
    ts_milli = 1672576200000
    assert webScrape.format_timestamp(ts_milli) == "2023-01-01T12:30:00Z"
    # Test invalid string
    assert webScrape.format_timestamp("invalid-date-string") is None
    assert webScrape.format_timestamp(None) is None

# Poți adăuga teste pentru fetch_url_with_retry folosind mocker de la pytest-mock
# pentru a simula răspunsurile requests.get
def test_fetch_url_with_retry_success(mocker):
    """Test successful URL fetch."""
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.content = b"Test content"
    mock_response.raise_for_status = mocker.Mock() # Mock this to do nothing on success

    mocker.patch('requests.get', return_value=mock_response)
    webScrape.REQUESTS_AVAILABLE = True # Ensure this is true for the test
    content = webScrape.fetch_url_with_retry("http://example.com")
    assert content == b"Test content"
    requests.get.assert_called_once_with("http://example.com", headers=None, timeout=webScrape.REQUEST_TIMEOUT)

def test_fetch_url_with_retry_failure(mocker):
    """Test URL fetch failure after retries."""
    mocker.patch('requests.get', side_effect=requests.exceptions.RequestException("Test error"))
    mocker.patch('time.sleep', return_value=None) # Speed up test by not actually sleeping
    webScrape.REQUESTS_AVAILABLE = True
    content = webScrape.fetch_url_with_retry("http://example.com")
    assert content is None
    assert requests.get.call_count == webScrape.MAX_RETRIES

# Notă: Testarea funcțiilor get_rss_news, get_newsapi_news, get_yfinance_news
# este mai complexă deoarece implică apeluri de rețea.
# Ar trebui să folosești 'mocker' extensiv pentru a simula răspunsurile API.
# Acest lucru depășește un exemplu simplu, dar ideea este să simulezi
# răspunsurile de la feedparser.parse, newsapi.get_everything, yf.Ticker().news etc.