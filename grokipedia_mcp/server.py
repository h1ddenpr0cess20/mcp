from fastmcp import FastMCP

from grokipedia_client import GrokipediaScraper

mcp = FastMCP("grokipedia")

_scraper = GrokipediaScraper()

@mcp.tool
def scrape_grokipedia(page_title: str) -> dict:
    """
    Scrape a Grokipedia page and return structured JSON.

    Args:
        page_title: The page title (e.g., "Elon Musk").

    Returns:
        dict with keys: page_title, url, content (list of sections).
    """
    return _scraper.scrape_page(page_title)

if __name__ == "__main__":
    # Default transport is STDIO; great for local dev / MCP clients.
    mcp.run()
    # mcp.run(transport="http", host="127.0.0.1", port=8000, path="/mcp")
    # mcp.run(transport="sse",  host="127.0.0.1", port=8000)
