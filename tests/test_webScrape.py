import pytest
import requests
from website.crucialPys import webScrape
from datetime import datetime, timezone
import time

SAMPLE_HTML_SUMMARY = "<p>This is a <b>test</b> summary. & some entities.</p> <!-- comment -->"
EXPECTED_CLEAN_SUMMARY = "This is a test summary. & some entities."

def test_clean_html_summary():
    """Test the HTML cleaning function."""

    webScrape.BS4_AVAILABLE = True
    assert webScrape.clean_html_summary(SAMPLE_HTML_SUMMARY) == EXPECTED_CLEAN_SUMMARY
    assert webScrape.clean_html_summary(None) == "N/A"
    assert webScrape.clean_html_summary("") == "N/A"
    assert webScrape.clean_html_summary("No HTML here.") == "No HTML here."

def test_format_timestamp_from_parsed():
    """Test formatting timestamp from time.struct_time."""

    dt_obj = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    parsed_time_struct = dt_obj.timetuple()

    utc_dt = datetime(2023, 1, 1, 10, 30, 0, tzinfo=timezone.utc)

    test_dt = datetime(2023, 5, 15, 12, 0, 0, tzinfo=timezone.utc)

    struct_time_utc = time.gmtime(test_dt.timestamp())

    expected_iso = "2023-05-15T12:00:00Z"
    assert webScrape.format_timestamp_from_parsed(struct_time_utc) == expected_iso
    assert webScrape.format_timestamp_from_parsed(None) is None

def test_format_timestamp_various_inputs():
    """Test formatting timestamp from various string and numeric inputs."""

    assert webScrape.format_timestamp("2023-01-01T12:30:00Z") == "2023-01-01T12:30:00Z"

    assert webScrape.format_timestamp("2023-01-01T12:30:00+02:00") == "2023-01-01T10:30:00Z"

    assert webScrape.format_timestamp("2023-01-01 12:30:00") == "2023-01-01T12:30:00Z"

    ts_sec = 1672576200
    assert webScrape.format_timestamp(ts_sec) == "2023-01-01T12:30:00Z"

    ts_milli = 1672576200000
    assert webScrape.format_timestamp(ts_milli) == "2023-01-01T12:30:00Z"

    assert webScrape.format_timestamp("invalid-date-string") is None
    assert webScrape.format_timestamp(None) is None

def test_fetch_url_with_retry_success(mocker):
    """Test successful URL fetch."""
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.content = b"Test content"
    mock_response.raise_for_status = mocker.Mock()

    mocker.patch('requests.get', return_value=mock_response)
    webScrape.REQUESTS_AVAILABLE = True
    content = webScrape.fetch_url_with_retry("http://example.com")
    assert content == b"Test content"
    requests.get.assert_called_once_with("http://example.com", headers=None, timeout=webScrape.REQUEST_TIMEOUT)

def test_fetch_url_with_retry_failure(mocker):
    """Test URL fetch failure after retries."""
    mocker.patch('requests.get', side_effect=requests.exceptions.RequestException("Test error"))
    mocker.patch('time.sleep', return_value=None)
    webScrape.REQUESTS_AVAILABLE = True
    content = webScrape.fetch_url_with_retry("http://example.com")
    assert content is None
    assert requests.get.call_count == webScrape.MAX_RETRIES

import pytest
import requests
from website.crucialPys import webScrape
from datetime import datetime, timezone
import time

SAMPLE_HTML_SUMMARY = "<p>This is a <b>test</b> summary. & some entities.</p> <!-- comment -->"
EXPECTED_CLEAN_SUMMARY = "This is a test summary. & some entities."

def test_clean_html_summary():
    """Test the HTML cleaning function."""

    webScrape.BS4_AVAILABLE = True
    assert webScrape.clean_html_summary(SAMPLE_HTML_SUMMARY) == EXPECTED_CLEAN_SUMMARY
    assert webScrape.clean_html_summary(None) == "N/A"
    assert webScrape.clean_html_summary("") == "N/A"
    assert webScrape.clean_html_summary("No HTML here.") == "No HTML here."

def test_format_timestamp_from_parsed():
    """Test formatting timestamp from time.struct_time."""

    dt_obj = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    parsed_time_struct = dt_obj.timetuple()

    utc_dt = datetime(2023, 1, 1, 10, 30, 0, tzinfo=timezone.utc)

    test_dt = datetime(2023, 5, 15, 12, 0, 0, tzinfo=timezone.utc)

    struct_time_utc = time.gmtime(test_dt.timestamp())

    expected_iso = "2023-05-15T12:00:00Z"
    assert webScrape.format_timestamp_from_parsed(struct_time_utc) == expected_iso
    assert webScrape.format_timestamp_from_parsed(None) is None

def test_format_timestamp_various_inputs():
    """Test formatting timestamp from various string and numeric inputs."""

    assert webScrape.format_timestamp("2023-01-01T12:30:00Z") == "2023-01-01T12:30:00Z"

    assert webScrape.format_timestamp("2023-01-01T12:30:00+02:00") == "2023-01-01T10:30:00Z"

    assert webScrape.format_timestamp("2023-01-01 12:30:00") == "2023-01-01T12:30:00Z"

    ts_sec = 1672576200
    assert webScrape.format_timestamp(ts_sec) == "2023-01-01T12:30:00Z"

    ts_milli = 1672576200000
    assert webScrape.format_timestamp(ts_milli) == "2023-01-01T12:30:00Z"

    assert webScrape.format_timestamp("invalid-date-string") is None
    assert webScrape.format_timestamp(None) is None

def test_fetch_url_with_retry_success(mocker):
    """Test successful URL fetch."""
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.content = b"Test content"
    mock_response.raise_for_status = mocker.Mock()

    mocker.patch('requests.get', return_value=mock_response)
    webScrape.REQUESTS_AVAILABLE = True
    content = webScrape.fetch_url_with_retry("http://example.com")
    assert content == b"Test content"
    requests.get.assert_called_once_with("http://example.com", headers=None, timeout=webScrape.REQUEST_TIMEOUT)

def test_fetch_url_with_retry_failure(mocker):
    """Test URL fetch failure after retries."""
    mocker.patch('requests.get', side_effect=requests.exceptions.RequestException("Test error"))
    mocker.patch('time.sleep', return_value=None)
    webScrape.REQUESTS_AVAILABLE = True
    content = webScrape.fetch_url_with_retry("http://example.com")
    assert content is None
    assert requests.get.call_count == webScrape.MAX_RETRIES

