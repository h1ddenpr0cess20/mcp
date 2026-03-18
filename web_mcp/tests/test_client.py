import pytest
from unittest.mock import MagicMock, patch

import httpx

from web_client.search import SearchClient
from web_client.fetch import FetchClient


class TestSearchClient:

    def test_search_returns_results(self, mock_search_response):
        """Test that search returns parsed results list."""
        with patch("web_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_search_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8888")
            results = client.search("python")

            assert isinstance(results, list)
            assert len(results) == 3
            assert results[0]["title"] == "Welcome to Python.org"
            assert results[0]["url"] == "https://www.python.org/"

    def test_search_respects_max_results(self, mock_search_response):
        """Test that max_results truncates the returned list."""
        with patch("web_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_search_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8888")
            results = client.search("python", max_results=2)

            assert len(results) == 2

    def test_search_passes_query_params(self, mock_search_response):
        """Test that search parameters are forwarded to the API."""
        with patch("web_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_search_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8888")
            client.search(
                "python",
                categories="news",
                language="fr",
                time_range="week",
                engines="brave",
                safesearch=1,
                pageno=2,
            )

            _, kwargs = mock_get.call_args
            params = kwargs["params"]
            assert params["q"] == "python"
            assert params["categories"] == "news"
            assert params["language"] == "fr"
            assert params["time_range"] == "week"
            assert params["engines"] == "brave"
            assert params["safesearch"] == 1
            assert params["pageno"] == 2
            assert params["format"] == "json"

    def test_search_omits_none_params(self, mock_search_response):
        """Test that None optional params are not included in the request."""
        with patch("web_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_search_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8888")
            client.search("python")

            _, kwargs = mock_get.call_args
            params = kwargs["params"]
            assert "categories" not in params
            assert "time_range" not in params
            assert "engines" not in params

    def test_search_empty_results(self, mock_empty_response):
        """Test that empty results are returned as an empty list."""
        with patch("web_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_empty_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8888")
            results = client.search("xyznonexistentquery")

            assert results == []

    def test_search_raises_on_http_error(self):
        """Test that HTTP errors propagate."""
        with patch("web_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500", request=MagicMock(), response=MagicMock()
            )
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8888")
            with pytest.raises(httpx.HTTPStatusError):
                client.search("python")

    def test_search_hits_correct_endpoint(self, mock_search_response):
        """Test that the search endpoint URL is constructed correctly."""
        with patch("web_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_search_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8888")
            client.search("python")

            args, _ = mock_get.call_args
            assert args[0] == "http://127.0.0.1:8888/search"

    def test_search_strips_trailing_slash_from_base_url(self, mock_search_response):
        """Test that trailing slashes on the base URL are handled."""
        with patch("web_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_search_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8888/")
            client.search("python")

            args, _ = mock_get.call_args
            assert args[0] == "http://127.0.0.1:8888/search"

    def test_news_search_uses_news_category(self, mock_news_response):
        """Test that news search sets categories=news."""
        with patch("web_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_news_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8888")
            results = client.search("python release", categories="news", time_range="week")

            _, kwargs = mock_get.call_args
            assert kwargs["params"]["categories"] == "news"
            assert kwargs["params"]["time_range"] == "week"
            assert len(results) == 2


class TestFetchClient:

    def test_fetch_returns_dict(self, mock_httpx_response):
        """Test that fetch returns a dict with url, title, and content."""
        with patch("web_client.fetch.httpx.get") as mock_get:
            mock_get.return_value = mock_httpx_response

            client = FetchClient()
            result = client.fetch("https://example.com")

            assert isinstance(result, dict)
            assert "url" in result
            assert "title" in result
            assert "content" in result

    def test_fetch_url_is_preserved(self, mock_httpx_response):
        """Test that the url field matches what was requested."""
        with patch("web_client.fetch.httpx.get") as mock_get:
            mock_get.return_value = mock_httpx_response

            client = FetchClient()
            result = client.fetch("https://example.com/page")

            assert result["url"] == "https://example.com/page"

    def test_fetch_markdown_format(self, mock_httpx_response):
        """Test that markdown output format returns non-empty content."""
        with patch("web_client.fetch.httpx.get") as mock_get:
            mock_get.return_value = mock_httpx_response

            client = FetchClient()
            result = client.fetch("https://example.com", output_format="markdown")

            assert isinstance(result["content"], str)
            assert len(result["content"]) > 0

    def test_fetch_text_format(self, mock_httpx_response):
        """Test that text output format returns string content."""
        with patch("web_client.fetch.httpx.get") as mock_get:
            mock_get.return_value = mock_httpx_response

            client = FetchClient()
            result = client.fetch("https://example.com", output_format="text")

            assert isinstance(result["content"], str)

    def test_fetch_html_format(self, mock_httpx_response, sample_html):
        """Test that html output format returns the raw HTML."""
        with patch("web_client.fetch.httpx.get") as mock_get:
            mock_get.return_value = mock_httpx_response

            client = FetchClient()
            result = client.fetch("https://example.com", output_format="html")

            assert result["content"] == sample_html

    def test_fetch_raises_on_http_error(self):
        """Test that HTTP errors from the target URL propagate."""
        with patch("web_client.fetch.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404", request=MagicMock(), response=MagicMock()
            )
            mock_get.return_value = mock_resp

            client = FetchClient()
            with pytest.raises(httpx.HTTPStatusError):
                client.fetch("https://example.com/notfound")

    def test_fetch_sends_user_agent(self, mock_httpx_response):
        """Test that a User-Agent header is sent with the request."""
        with patch("web_client.fetch.httpx.get") as mock_get:
            mock_get.return_value = mock_httpx_response

            client = FetchClient()
            client.fetch("https://example.com")

            _, kwargs = mock_get.call_args
            assert "User-Agent" in kwargs["headers"]
            assert "Mozilla" in kwargs["headers"]["User-Agent"]

    def test_fetch_follows_redirects(self, mock_httpx_response):
        """Test that redirects are followed."""
        with patch("web_client.fetch.httpx.get") as mock_get:
            mock_get.return_value = mock_httpx_response

            client = FetchClient()
            client.fetch("https://example.com")

            _, kwargs = mock_get.call_args
            assert kwargs.get("follow_redirects") is True
