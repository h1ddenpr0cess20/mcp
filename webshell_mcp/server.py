import atexit
import os
import signal
import sys
import threading
from typing import Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

from webshell_client import FetchClient, FileServer, SearchClient, ShellClient
from webshell_client.vm_manager import VMManager

load_dotenv()

_vm = VMManager()
atexit.register(_vm.stop_vm)


def _handle_signal(signum, frame):
    sys.exit(0)


signal.signal(signal.SIGTERM, _handle_signal)

SEARXNG_TIMEOUT = float(os.environ.get("SEARXNG_TIMEOUT", "30"))
FETCH_TIMEOUT = float(os.environ.get("FETCH_TIMEOUT", "30"))
FETCH_PROXIES = [p.strip() for p in os.environ.get("FETCH_PROXIES", "").split(",") if p.strip()]

# VM bring-up (create/restore/boot/wait-for-SSH, then SearXNG) can take
# anywhere from seconds to tens of minutes. Do it on a background thread so
# the MCP transport starts answering the handshake immediately instead of
# looking hung/offline to the client for the whole duration; tool calls
# block on the _get_*() accessors below until it's ready.
_client: ShellClient | None = None
_search: SearchClient | None = None
_fetch: FetchClient | None = None
_client_ready = threading.Event()
_client_error: Exception | None = None


def _bring_up_vm():
    global _client, _search, _fetch, _client_error
    try:
        conn = _vm.ensure_running()
        _client = ShellClient(host=conn["ssh_host"], port=conn["ssh_port"])
        searxng_url = os.environ.get("SEARXNG_URL") or conn["searxng_url"]
        _search = SearchClient(searxng_url, timeout=SEARXNG_TIMEOUT)
        _fetch = FetchClient(_client, timeout=FETCH_TIMEOUT, proxies=FETCH_PROXIES or None)
    except Exception as exc:
        _client_error = exc
    finally:
        _client_ready.set()


threading.Thread(target=_bring_up_vm, daemon=True, name="vm-bringup").start()


def _wait_ready() -> None:
    _client_ready.wait()
    if _client_error is not None:
        raise RuntimeError(f"Sandbox failed to start: {_client_error}")


def _get_client() -> ShellClient:
    """Block until the sandbox VM is ready, then return the shell client.

    Only tool calls wait here — the MCP transport itself starts responding
    to the protocol handshake right away, without waiting on the VM.
    """
    _wait_ready()
    return _client


def _get_search() -> SearchClient:
    _wait_ready()
    return _search


def _get_fetch() -> FetchClient:
    _wait_ready()
    return _fetch


_file_server = FileServer()

mcp = FastMCP("webshell")

_file_server.start()


# ── Shell tools ──────────────────────────────────────────────────────────────

@mcp.tool
def execute_command(command: str) -> dict:
    """Execute a shell command in the sandbox (an isolated Linux VM).

    Use for installing packages, running scripts, compiling code, processing
    data, or anything requiring pipes, redirection, or shell features.

    Args:
        command: Bash command or pipeline to run, e.g. "ls -la /tmp" or
            "python3 script.py | grep error".

    Returns:
        Dict with stdout (str), stderr (str), and exit_code (int).
    """
    return _get_client().execute(command)


@mcp.tool
def list_directory(path: str = "~") -> list[dict]:
    """List files and directories at the given path in the sandbox.

    Args:
        path: Directory path on the sandbox (default: "~", the home dir).

    Returns:
        List of file entries with name, size, is_dir, permissions, and modified.
    """
    return _get_client().list_remote(path)


@mcp.tool
def read_file(path: str) -> str:
    """Read the text contents of a file in the sandbox.

    Args:
        path: Absolute path to the file on the sandbox, e.g. "/home/ai-agent/script.py".

    Returns:
        File contents as a string.
    """
    return _get_client().read_remote(path)


@mcp.tool
def write_file(path: str, content: str) -> dict:
    """Write text content to a file in the sandbox, creating or overwriting it.

    For uploading a binary or existing local file use upload_file instead.
    Parent directories must exist; create them first with execute_command if needed.

    Args:
        path: Absolute destination path on the sandbox, e.g. "/home/ai-agent/script.py".
        content: Text content to write. Replaces existing content entirely.

    Returns:
        Dict with path (str) and size (int).
    """
    return _get_client().write_remote(path, content)


@mcp.tool
def upload_file(local_path: str, remote_path: str) -> dict:
    """Upload a file from the local host into the sandbox via SFTP.

    Use for binary files or existing local files. For text you have in memory,
    use write_file instead.

    Args:
        local_path: Absolute path on the LOCAL machine, e.g. "/home/user/data.csv".
        remote_path: Destination absolute path on the SANDBOX, e.g. "/home/ai-agent/data.csv".

    Returns:
        Dict with remote_path (str) and size (int).
    """
    return _get_client().upload(local_path, remote_path)


@mcp.tool
def download_file(remote_path: str, local_path: str) -> dict:
    """Download a file from the sandbox to the local machine via SFTP.

    Use to save a sandbox file to a specific local path. To serve a file to a
    client via HTTP URL (e.g. a generated PDF), use fetch_file instead.

    Args:
        remote_path: Absolute path on the SANDBOX, e.g. "/home/ai-agent/output.zip".
        local_path: Destination absolute path on the LOCAL machine, e.g. "/tmp/output.zip".

    Returns:
        Dict with local_path (str) and size (int).
    """
    return _get_client().download(remote_path, local_path)


@mcp.tool
def get_system_info() -> dict:
    """Get hostname, uptime, memory usage, and disk usage from the sandbox.

    Returns:
        Dict with system information fields.
    """
    return _get_client().system_info()


@mcp.tool
def fetch_file(remote_path: str) -> dict:
    """Serve a sandbox file to the client via an HTTP download URL.

    Use after the sandbox generates a document, image, or archive that the
    client needs to download (PDF, Word, spreadsheet, zip, etc.). To save to
    a local path instead, use download_file.

    Args:
        remote_path: Absolute path to the file on the SANDBOX, e.g. "/home/ai-agent/report.pdf".

    Returns:
        Dict with file_id, filename, size, mime_type, and url.
    """
    filename = os.path.basename(remote_path)
    local_path = str(_file_server.files_dir / filename)
    result = _get_client().download(remote_path, local_path)
    return _file_server.register(local_path, filename, result["size"])


# ── Web tools ────────────────────────────────────────────────────────────────

@mcp.tool
def web_search(
    query: str,
    categories: Optional[str] = None,
    language: str = "en",
    time_range: Optional[str] = None,
    max_results: int = 10,
    engines: Optional[str] = None,
    safesearch: int = 0,
    pageno: int = 1,
):
    """Search the web using SearXNG. Supports all major search categories.

    Args:
        query: Search query. Supports operators like site:, intitle:, inurl:, etc.
        categories: Comma-separated categories (general, images, news, videos, music, files, it, science, social media, map).
        language: Language code (e.g. "en", "fr", "de").
        time_range: Time filter: "day", "week", "month", or "year".
        max_results: Maximum number of results (default 10).
        engines: Comma-separated engine names to query.
        safesearch: 0=off, 1=moderate, 2=strict.
        pageno: Page number for pagination.

    Returns:
        List of search results with title, url, content, engine, and score.
    """
    return _get_search().search(
        query,
        categories=categories,
        language=language,
        time_range=time_range,
        max_results=max_results,
        engines=engines,
        safesearch=safesearch,
        pageno=pageno,
    )


@mcp.tool
def news_search(
    query: str,
    language: str = "en",
    time_range: str = "week",
    max_results: int = 10,
):
    """Search for recent news articles using SearXNG.

    Args:
        query: News search query.
        language: Language code.
        time_range: Time filter: "day", "week", "month", or "year".
        max_results: Maximum number of results.

    Returns:
        List of news results.
    """
    return _get_search().search(
        query,
        categories="news",
        language=language,
        time_range=time_range,
        max_results=max_results,
    )


@mcp.tool
def fetch_url(
    url: str,
    output_format: str = "markdown",
    include_links: bool = True,
):
    """Fetch a URL and extract its content as markdown, text, or raw HTML.

    Args:
        url: The URL to fetch.
        output_format: "markdown" (default), "text", or "html".
        include_links: Whether to include links in extracted content.

    Returns:
        Dict with url, title, and content.
    """
    return _get_fetch().fetch(
        url,
        output_format=output_format,
        include_links=include_links,
    )


@mcp.tool
def scrape_url(
    url: str,
    output_format: str = "markdown",
    include_links: bool = True,
):
    """Scrape a URL using a headless Playwright browser in the sandbox.

    Use this when fetch_url returns empty or broken content — typically for
    JavaScript-rendered pages (SPAs, dashboards, dynamically loaded content).
    This is slower than fetch_url but handles JS-heavy sites that curl cannot render.

    Args:
        url: The URL to scrape.
        output_format: "markdown" (default), "text", or "html".
        include_links: Whether to include links in extracted content.

    Returns:
        Dict with url, title, and content.
    """
    return _get_fetch().scrape(
        url,
        output_format=output_format,
        include_links=include_links,
    )


if __name__ == "__main__":
    import sys
    if sys.stdin.isatty():
        mcp.run(transport="http", host="127.0.0.1", port=9710, path="/mcp")
    else:
        mcp.run()
