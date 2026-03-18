import pytest
from unittest.mock import MagicMock, patch

import httpx
from curl_cffi.requests.exceptions import HTTPError

from web_client.search import SearchClient
from web_client.fetch import FetchClient, _JS_FALLBACK_THRESHOLD


class TestSearchClient:

    def test_search_returns_results(self, mock_search_response):
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
        with patch("web_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_search_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8888")
            results = client.search("python", max_results=2)

            assert len(results) == 2

    def test_search_passes_query_params(self, mock_search_response):
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
        with patch("web_client.search.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_empty_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            client = SearchClient("http://127.0.0.1:8888")
            results = client.search("xyznonexistentquery")

            assert results == []

    def test_search_raises_on_http_error(self):
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

    def _patch_fetch(self, mock_curl_response):
        """Context manager that patches both curl_cffi and playwright fallback."""
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            with patch("web_client.fetch.requests.get") as mock_get, \
                 patch.object(FetchClient, "_fetch_with_playwright", return_value=""):
                mock_get.return_value = mock_curl_response
                yield mock_get
        return _ctx()

    def test_fetch_returns_dict(self, mock_curl_response):
        with self._patch_fetch(mock_curl_response):
            client = FetchClient()
            result = client.fetch("https://example.com")

            assert isinstance(result, dict)
            assert "url" in result
            assert "title" in result
            assert "content" in result

    def test_fetch_url_is_preserved(self, mock_curl_response):
        with self._patch_fetch(mock_curl_response):
            client = FetchClient()
            result = client.fetch("https://example.com/page")

            assert result["url"] == "https://example.com/page"

    def test_fetch_markdown_format(self, mock_curl_response):
        with self._patch_fetch(mock_curl_response):
            client = FetchClient()
            result = client.fetch("https://example.com", output_format="markdown")

            assert isinstance(result["content"], str)
            assert len(result["content"]) > 0

    def test_fetch_text_format(self, mock_curl_response):
        with self._patch_fetch(mock_curl_response):
            client = FetchClient()
            result = client.fetch("https://example.com", output_format="text")

            assert isinstance(result["content"], str)

    def test_fetch_html_format(self, mock_curl_response, sample_html):
        with self._patch_fetch(mock_curl_response):
            client = FetchClient()
            result = client.fetch("https://example.com", output_format="html")

            assert result["content"] == sample_html

    def test_fetch_raises_on_http_error(self):
        with patch("web_client.fetch.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = HTTPError(
                "404", 0, MagicMock()
            )
            mock_get.return_value = mock_resp

            client = FetchClient()
            with pytest.raises(HTTPError):
                client.fetch("https://example.com/notfound")

    def test_fetch_uses_chrome_impersonation(self, mock_curl_response):
        with self._patch_fetch(mock_curl_response) as mock_get:
            client = FetchClient()
            client.fetch("https://example.com")

            _, kwargs = mock_get.call_args
            assert kwargs["impersonate"] == "chrome"

    def test_fetch_follows_redirects(self, mock_curl_response):
        with self._patch_fetch(mock_curl_response) as mock_get:
            client = FetchClient()
            client.fetch("https://example.com")

            _, kwargs = mock_get.call_args
            assert kwargs["allow_redirects"] is True

    def test_fetch_passes_proxy(self, mock_curl_response):
        with patch("web_client.fetch.requests.get") as mock_get, \
             patch.object(FetchClient, "_fetch_with_playwright", return_value=""):
            mock_get.return_value = mock_curl_response

            client = FetchClient(proxies=["http://proxy:8080"])
            client.fetch("https://example.com")

            _, kwargs = mock_get.call_args
            assert kwargs["proxy"] == "http://proxy:8080"

    def test_fetch_no_proxy_by_default(self, mock_curl_response):
        with self._patch_fetch(mock_curl_response) as mock_get:
            client = FetchClient()
            client.fetch("https://example.com")

            _, kwargs = mock_get.call_args
            assert "proxy" not in kwargs

    def test_fetch_rotates_proxies(self, mock_curl_response):
        with patch("web_client.fetch.requests.get") as mock_get, \
             patch.object(FetchClient, "_fetch_with_playwright", return_value=""):
            mock_get.return_value = mock_curl_response

            proxies = ["http://proxy1:8080", "http://proxy2:8080", "http://proxy3:8080"]
            client = FetchClient(proxies=proxies)

            used = set()
            for _ in range(50):
                client.fetch("https://example.com")
                _, kwargs = mock_get.call_args
                used.add(kwargs["proxy"])

            assert len(used) > 1

    def test_js_fallback_triggers_on_short_content(self):
        short_html = "<html><body><script>render()</script></body></html>"
        mock_resp = MagicMock()
        mock_resp.text = short_html
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None

        full_html = """<html><head><title>Full Page</title></head>
        <body><article><p>{}</p></article></body></html>""".format("x" * 600)

        with patch("web_client.fetch.requests.get") as mock_get, \
             patch.object(FetchClient, "_fetch_with_playwright") as mock_pw:
            mock_get.return_value = mock_resp
            mock_pw.return_value = full_html

            client = FetchClient()
            result = client.fetch("https://js-heavy-site.com")

            mock_pw.assert_called_once_with("https://js-heavy-site.com")
            assert len(result["content"]) >= _JS_FALLBACK_THRESHOLD

    def test_js_fallback_skipped_on_long_content(self):
        long_html = """<html><head><title>Big Article</title></head>
        <body><article>{}</article></body></html>""".format(
            "".join(f"<p>Paragraph {i} with enough text to pass threshold.</p>" for i in range(50))
        )
        mock_resp = MagicMock()
        mock_resp.text = long_html
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None

        with patch("web_client.fetch.requests.get") as mock_get, \
             patch.object(FetchClient, "_fetch_with_playwright") as mock_pw:
            mock_get.return_value = mock_resp

            client = FetchClient()
            client.fetch("https://example.com")

            mock_pw.assert_not_called()

    def test_js_fallback_error_returns_original(self):
        short_html = "<html><body>tiny</body></html>"
        mock_resp = MagicMock()
        mock_resp.text = short_html
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None

        with patch("web_client.fetch.requests.get") as mock_get, \
             patch.object(FetchClient, "_fetch_with_playwright") as mock_pw:
            mock_get.return_value = mock_resp
            mock_pw.side_effect = RuntimeError("browser failed")

            client = FetchClient()
            result = client.fetch("https://example.com")

            assert isinstance(result, dict)
            assert result["url"] == "https://example.com"

    def test_playwright_receives_proxy(self):
        short_html = "<html><body>tiny</body></html>"
        mock_resp = MagicMock()
        mock_resp.text = short_html
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None

        full_html = """<html><head><title>Full</title></head>
        <body><article><p>{}</p></article></body></html>""".format("x" * 600)

        with patch("web_client.fetch.requests.get") as mock_get, \
             patch("web_client.fetch.sync_playwright") as mock_pw_ctx:
            mock_get.return_value = mock_resp

            mock_browser = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = full_html
            mock_browser.new_page.return_value = mock_page
            mock_pw = MagicMock()
            mock_pw.chromium.launch.return_value = mock_browser
            mock_pw_ctx.return_value.__enter__ = MagicMock(return_value=mock_pw)
            mock_pw_ctx.return_value.__exit__ = MagicMock(return_value=False)

            client = FetchClient(proxies=["socks5://proxy:1080"])
            client.fetch("https://js-site.com")

            launch_kwargs = mock_pw.chromium.launch.call_args[1]
            assert launch_kwargs["proxy"] == {"server": "socks5://proxy:1080"}
