import json

import pytest
from unittest.mock import MagicMock, patch, call

from webshell_client.fetch import FetchClient


def _mock_shell(stdout="", stderr="", exit_code=0):
    """Create a mock ShellClient with canned execute results."""
    shell = MagicMock()
    shell.execute.return_value = {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
    }
    shell.write_remote.return_value = {"path": ".webshell-mcp/fetch.py", "size": 100}
    return shell


class TestFetchClientInit:

    def test_stores_shell_and_defaults(self):
        shell = MagicMock()
        client = FetchClient(shell)
        assert client.shell is shell
        assert client.timeout == 30.0
        assert client.proxies == []
        assert client._deployed is False

    def test_stores_custom_timeout_and_proxies(self):
        shell = MagicMock()
        client = FetchClient(shell, timeout=60.0, proxies=["http://proxy:8080"])
        assert client.timeout == 60.0
        assert client.proxies == ["http://proxy:8080"]


class TestEnsureDeployed:

    def test_deploys_script_on_first_call(self):
        shell = _mock_shell()
        client = FetchClient(shell)
        client._ensure_deployed()

        shell.execute.assert_called_once_with("mkdir -p ~/.webshell-mcp")
        shell.write_remote.assert_called_once()
        assert client._deployed is True

    def test_skips_deploy_on_subsequent_calls(self):
        shell = _mock_shell()
        client = FetchClient(shell)
        client._ensure_deployed()
        client._ensure_deployed()

        # mkdir and write_remote should only be called once
        assert shell.execute.call_count == 1
        assert shell.write_remote.call_count == 1


class TestFetch:

    def test_returns_parsed_json_on_success(self):
        result_json = json.dumps({
            "url": "https://example.com",
            "title": "Example",
            "content": "Hello world",
        })
        shell = _mock_shell(stdout=result_json)
        client = FetchClient(shell)

        result = client.fetch("https://example.com")

        assert result["url"] == "https://example.com"
        assert result["title"] == "Example"
        assert result["content"] == "Hello world"

    def test_returns_error_on_nonzero_exit(self):
        shell = _mock_shell(stderr="connection refused", exit_code=1)
        client = FetchClient(shell)

        result = client.fetch("https://bad.example.com")

        assert result["url"] == "https://bad.example.com"
        assert result["title"] == ""
        assert "connection refused" in result["content"]

    def test_passes_output_format(self):
        result_json = json.dumps({"url": "u", "title": "t", "content": "c"})
        shell = _mock_shell(stdout=result_json)
        client = FetchClient(shell)

        client.fetch("https://example.com", output_format="text")

        cmd = shell.execute.call_args_list[-1][0][0]
        args = json.loads(cmd.split("'")[1])
        assert args["output_format"] == "text"

    def test_passes_include_links(self):
        result_json = json.dumps({"url": "u", "title": "t", "content": "c"})
        shell = _mock_shell(stdout=result_json)
        client = FetchClient(shell)

        client.fetch("https://example.com", include_links=False)

        cmd = shell.execute.call_args_list[-1][0][0]
        args = json.loads(cmd.split("'")[1])
        assert args["include_links"] is False

    def test_passes_timeout_and_proxies(self):
        result_json = json.dumps({"url": "u", "title": "t", "content": "c"})
        shell = _mock_shell(stdout=result_json)
        proxies = ["http://p1:8080", "socks5://p2:1080"]
        client = FetchClient(shell, timeout=45.0, proxies=proxies)

        client.fetch("https://example.com")

        cmd = shell.execute.call_args_list[-1][0][0]
        args = json.loads(cmd.split("'")[1])
        assert args["timeout"] == 45.0
        assert args["proxies"] == proxies

    def test_ssh_timeout_is_2x_fetch_timeout(self):
        result_json = json.dumps({"url": "u", "title": "t", "content": "c"})
        shell = _mock_shell(stdout=result_json)
        client = FetchClient(shell, timeout=20.0)

        client.fetch("https://example.com")

        _, kwargs = shell.execute.call_args_list[-1]
        assert kwargs["timeout"] == 40  # 20 * 2

    def test_deploys_script_before_first_fetch(self):
        result_json = json.dumps({"url": "u", "title": "t", "content": "c"})
        shell = _mock_shell(stdout=result_json)
        client = FetchClient(shell)

        assert client._deployed is False
        client.fetch("https://example.com")
        assert client._deployed is True

    def test_executes_correct_remote_command(self):
        result_json = json.dumps({"url": "u", "title": "t", "content": "c"})
        shell = _mock_shell(stdout=result_json)
        client = FetchClient(shell)

        client.fetch("https://example.com")

        cmd = shell.execute.call_args_list[-1][0][0]
        assert cmd.startswith("python3 .webshell-mcp/fetch.py")

    def test_escapes_single_quotes_in_url(self):
        result_json = json.dumps({"url": "u", "title": "t", "content": "c"})
        shell = _mock_shell(stdout=result_json)
        client = FetchClient(shell)

        # URL with single quote would break shell if not escaped
        client.fetch("https://example.com/it's-a-test")

        cmd = shell.execute.call_args_list[-1][0][0]
        # The JSON args are wrapped in single quotes; any internal single
        # quotes must be escaped
        assert "it's-a-test" not in cmd or "'\\''" in cmd


class TestEnsureScrapeDeployed:

    def test_deploys_scrape_script_on_first_call(self):
        shell = _mock_shell()
        client = FetchClient(shell)
        client._ensure_scrape_deployed()

        shell.execute.assert_called_once_with("mkdir -p ~/.webshell-mcp")
        shell.write_remote.assert_called_once()
        assert client._scrape_deployed is True

    def test_skips_deploy_on_subsequent_calls(self):
        shell = _mock_shell()
        client = FetchClient(shell)
        client._ensure_scrape_deployed()
        client._ensure_scrape_deployed()

        assert shell.execute.call_count == 1
        assert shell.write_remote.call_count == 1


class TestScrape:

    def test_returns_parsed_json_on_success(self):
        result_json = json.dumps({
            "url": "https://spa.example.com",
            "title": "SPA Page",
            "content": "Rendered content",
        })
        shell = _mock_shell(stdout=result_json)
        client = FetchClient(shell)

        result = client.scrape("https://spa.example.com")

        assert result["url"] == "https://spa.example.com"
        assert result["title"] == "SPA Page"
        assert result["content"] == "Rendered content"

    def test_returns_error_on_nonzero_exit(self):
        shell = _mock_shell(stderr="playwright crash", exit_code=1)
        client = FetchClient(shell)

        result = client.scrape("https://bad.example.com")

        assert result["url"] == "https://bad.example.com"
        assert result["title"] == ""
        assert "playwright crash" in result["content"]

    def test_executes_correct_remote_command(self):
        result_json = json.dumps({"url": "u", "title": "t", "content": "c"})
        shell = _mock_shell(stdout=result_json)
        client = FetchClient(shell)

        client.scrape("https://example.com")

        cmd = shell.execute.call_args_list[-1][0][0]
        assert cmd.startswith("python3 .webshell-mcp/scrape.py")

    def test_ssh_timeout_is_3x_scrape_timeout(self):
        result_json = json.dumps({"url": "u", "title": "t", "content": "c"})
        shell = _mock_shell(stdout=result_json)
        client = FetchClient(shell, timeout=20.0)

        client.scrape("https://example.com")

        _, kwargs = shell.execute.call_args_list[-1]
        assert kwargs["timeout"] == 60  # 20 * 3

    def test_passes_output_format(self):
        result_json = json.dumps({"url": "u", "title": "t", "content": "c"})
        shell = _mock_shell(stdout=result_json)
        client = FetchClient(shell)

        client.scrape("https://example.com", output_format="html")

        cmd = shell.execute.call_args_list[-1][0][0]
        args = json.loads(cmd.split("'")[1])
        assert args["output_format"] == "html"

    def test_deploys_scrape_script_before_first_scrape(self):
        result_json = json.dumps({"url": "u", "title": "t", "content": "c"})
        shell = _mock_shell(stdout=result_json)
        client = FetchClient(shell)

        assert client._scrape_deployed is False
        client.scrape("https://example.com")
        assert client._scrape_deployed is True
