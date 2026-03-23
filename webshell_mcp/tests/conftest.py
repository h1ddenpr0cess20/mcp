import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_ssh_client(mocker):
    """Mock paramiko.SSHClient for unit tests."""
    mock_client = mocker.MagicMock()
    mock_transport = mocker.MagicMock()
    mock_transport.is_active.return_value = True
    mock_client.get_transport.return_value = mock_transport

    mock_stdin = MagicMock()
    mock_stdout = MagicMock()
    mock_stderr = MagicMock()
    mock_stdout.read.return_value = b""
    mock_stderr.read.return_value = b""
    mock_stdout.channel.recv_exit_status.return_value = 0
    mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

    mocker.patch("paramiko.SSHClient", return_value=mock_client)
    return mock_client


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
