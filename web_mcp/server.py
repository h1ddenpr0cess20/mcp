import os
from typing import Optional

from fastmcp import FastMCP

from web_client import FetchClient, SearchClient
from web_client._searxng import ensure_running

SEARXNG_URL = os.environ.get("SEARXNG_URL") or ensure_running()
SEARXNG_TIMEOUT = float(os.environ.get("SEARXNG_TIMEOUT", "30"))
FETCH_TIMEOUT = float(os.environ.get("FETCH_TIMEOUT", "30"))
FETCH_PROXIES = [p.strip() for p in os.environ.get("FETCH_PROXIES", "").split(",") if p.strip()]

_search = SearchClient(SEARXNG_URL, timeout=SEARXNG_TIMEOUT)
_fetch = FetchClient(timeout=FETCH_TIMEOUT, proxies=FETCH_PROXIES or None)

mcp = FastMCP("web")


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
    return _search.search(
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
    return _search.search(
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
    return _fetch.fetch(
        url,
        output_format=output_format,
        include_links=include_links,
    )


if __name__ == "__main__":
    import sys
    if sys.stdin.isatty():
        mcp.run(transport="http", host="127.0.0.1", port=9500, path="/mcp")
    else:
        mcp.run()
