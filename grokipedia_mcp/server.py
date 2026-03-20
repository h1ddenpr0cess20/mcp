from fastmcp import FastMCP

from grokipedia_client import GrokipediaScraper

mcp = FastMCP("grokipedia")

_scraper = GrokipediaScraper()


@mcp.tool
def scrape_grokipedia(
    page_title: str
) -> dict:
    """
    Scrape a Grokipedia page and return structured JSON.

    Args:
        page_title: The page title (e.g., "Elon Musk").

    Returns:
        dict with keys: page_title, url, content (list of sections),
        info_panels (list of structured panel objects).
    """
    return _scraper.scrape_page(page_title)


@mcp.tool
def search_grokipedia(
    query: str,
    page: int = 1
) -> dict:
    """
    Search Grokipedia for pages matching a query.

    Args:
        query: The search query string.
        page: Page number for pagination (default 1).

    Returns:
        dict with keys: query, page, results (list of dicts with
        title, slug, snippet, url), total_pages.
    """
    return _scraper.search(query, page)


if __name__ == "__main__":
    import sys
    if sys.stdin.isatty():
        mcp.run(transport="http", host="127.0.0.1", port=9101, path="/mcp")
    else:
        mcp.run()
