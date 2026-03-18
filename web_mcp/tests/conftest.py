import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_search_response():
    """Sample SearXNG JSON search response."""
    return {
        "query": "python",
        "number_of_results": 3,
        "results": [
            {
                "title": "Welcome to Python.org",
                "url": "https://www.python.org/",
                "content": "The official home of the Python programming language.",
                "engine": "brave",
                "engines": ["brave", "duckduckgo"],
                "score": 9.0,
                "publishedDate": None,
            },
            {
                "title": "Python Tutorial - W3Schools",
                "url": "https://www.w3schools.com/python/",
                "content": "Well organized tutorial for Python beginners.",
                "engine": "brave",
                "engines": ["brave"],
                "score": 4.5,
                "publishedDate": None,
            },
            {
                "title": "Learn Python - Codecademy",
                "url": "https://www.codecademy.com/learn/learn-python-3",
                "content": "Learn Python 3 interactively.",
                "engine": "duckduckgo",
                "engines": ["duckduckgo"],
                "score": 2.0,
                "publishedDate": None,
            },
        ],
    }


@pytest.fixture
def mock_news_response():
    """Sample SearXNG news search response."""
    return {
        "query": "python release",
        "number_of_results": 2,
        "results": [
            {
                "title": "Python 3.13 Released",
                "url": "https://www.python.org/downloads/release/python-3130/",
                "content": "Python 3.13 is now available.",
                "engine": "brave",
                "engines": ["brave"],
                "score": 5.0,
                "publishedDate": "2024-10-07T00:00:00",
            },
            {
                "title": "What's New in Python 3.13",
                "url": "https://docs.python.org/3.13/whatsnew/3.13.html",
                "content": "Overview of new features in Python 3.13.",
                "engine": "duckduckgo",
                "engines": ["duckduckgo"],
                "score": 3.0,
                "publishedDate": "2024-10-07T00:00:00",
            },
        ],
    }


@pytest.fixture
def mock_empty_response():
    """SearXNG response with no results."""
    return {
        "query": "xyznonexistentquery",
        "number_of_results": 0,
        "results": [],
    }


@pytest.fixture
def sample_html():
    """Sample HTML page for fetch testing."""
    return """<!DOCTYPE html>
<html>
<head><title>Test Article</title></head>
<body>
  <article>
    <h1>Test Article</h1>
    <p>This is the main content of the article.</p>
    <p>It has multiple paragraphs with useful information.</p>
  </article>
</body>
</html>"""


@pytest.fixture
def mock_httpx_response(sample_html):
    """Mock httpx.Response for fetch tests."""
    mock = MagicMock()
    mock.text = sample_html
    mock.status_code = 200
    mock.raise_for_status.return_value = None
    return mock
