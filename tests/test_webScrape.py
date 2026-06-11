import requests
import time
from datetime import datetime, timezone
from website.crucialPys import webScrape

SAMPLE_HTML_SUMMARY = "<p>This is a <b>test</b> summary. & some entities.</p> "
EXPECTED_CLEAN_SUMMARY = "This is a test summary. & some entities."

def test_clean_html_summary():
    webScrape.BS4_AVAILABLE = True
    assert webScrape.clean_html_summary(SAMPLE_HTML_SUMMARY) == EXPECTED_CLEAN_SUMMARY
    assert webScrape.clean_html_summary(None) == "N/A"
    assert webScrape.clean_html_summary("") == "N/A"
    assert webScrape.clean_html_summary("No HTML here.") == "No HTML here."

def test_format_timestamp_from_parsed():
    test_dt = datetime(2023, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    struct_time_utc = time.gmtime(test_dt.timestamp())
    expected_iso = "2023-05-15T12:00:00Z"
    
    assert webScrape.format_timestamp_from_parsed(struct_time_utc) == expected_iso
    assert webScrape.format_timestamp_from_parsed(None) is None

def test_format_timestamp_various_inputs():
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
    mocker.patch('requests.get', side_effect=requests.exceptions.RequestException("Test error"))
    mocker.patch('time.sleep', return_value=None)
    webScrape.REQUESTS_AVAILABLE = True

    content = webScrape.fetch_url_with_retry("http://example.com")

    assert content is None
    assert requests.get.call_count == webScrape.MAX_RETRIES


def test_normalize_yfinance_item_legacy_format():
    item = {
        "title": "Markets rally",
        "link": "https://example.com/a",
        "publisher": "Example News",
        "providerPublishTime": 1672576200,
    }
    article = webScrape._normalize_yfinance_item(item)
    assert article["title"] == "Markets rally"
    assert article["url"] == "https://example.com/a"
    assert article["summary"] == "Publisher: Example News"
    assert article["timestamp"] == "2023-01-01T12:30:00Z"


def test_normalize_yfinance_item_new_format():
    item = {
        "id": "abc",
        "content": {
            "title": "Stocks slide",
            "pubDate": "2023-01-01T12:30:00Z",
            "canonicalUrl": {"url": "https://example.com/b"},
            "provider": {"displayName": "Example Wire"},
        },
    }
    article = webScrape._normalize_yfinance_item(item)
    assert article["title"] == "Stocks slide"
    assert article["url"] == "https://example.com/b"
    assert article["summary"] == "Publisher: Example Wire"
    assert article["timestamp"] == "2023-01-01T12:30:00Z"


def test_normalize_yfinance_item_missing_link_returns_none():
    assert webScrape._normalize_yfinance_item({"title": "No link"}) is None
    assert webScrape._normalize_yfinance_item({"content": {"title": "No link"}}) is None
