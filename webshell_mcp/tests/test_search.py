import pytest
from unittest.mock import MagicMock, patch

import httpx

from webshell_client.search import SearchClient


class TestSearchClient:

    def test_search_returns_results(self, mock_search_response):
        with patch("webshell_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_search_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8889")
            results = client.search("python")

            assert isinstance(results, list)
            assert len(results) == 3
            assert results[0]["title"] == "Welcome to Python.org"
            assert results[0]["url"] == "https://www.python.org/"

    def test_search_respects_max_results(self, mock_search_response):
        with patch("webshell_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_search_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8889")
            results = client.search("python", max_results=2)

            assert len(results) == 2

    def test_search_passes_query_params(self, mock_search_response):
        with patch("webshell_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_search_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8889")
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
        with patch("webshell_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_search_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8889")
            client.search("python")

            _, kwargs = mock_get.call_args
            params = kwargs["params"]
            assert "categories" not in params
            assert "time_range" not in params
            assert "engines" not in params

    def test_search_empty_results(self, mock_empty_response):
        with patch("webshell_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_empty_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8889")
            results = client.search("xyznonexistentquery")

            assert results == []

    def test_search_raises_on_http_error(self):
        with patch("webshell_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500", request=MagicMock(), response=MagicMock()
            )
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8889")
            with pytest.raises(httpx.HTTPStatusError):
                client.search("python")

    def test_search_hits_correct_endpoint(self, mock_search_response):
        with patch("webshell_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_search_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8889")
            client.search("python")

            args, _ = mock_get.call_args
            assert args[0] == "http://127.0.0.1:8889/search"

    def test_search_strips_trailing_slash_from_base_url(self, mock_search_response):
        with patch("webshell_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_search_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8889/")
            client.search("python")

            args, _ = mock_get.call_args
            assert args[0] == "http://127.0.0.1:8889/search"

    def test_news_search_uses_news_category(self, mock_news_response):
        with patch("webshell_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_news_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8889")
            results = client.search("python release", categories="news", time_range="week")

            _, kwargs = mock_get.call_args
            assert kwargs["params"]["categories"] == "news"
            assert kwargs["params"]["time_range"] == "week"
            assert len(results) == 2
