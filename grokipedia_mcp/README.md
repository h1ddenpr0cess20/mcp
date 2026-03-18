# Grokipedia MCP Server (FastMCP)

This project provides an MCP server for scraping Grokipedia pages using **FastMCP**.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python server.py  # runs an MCP server; see FastMCP docs for client hookup
```

## Description

The server exposes two tools:

- **`scrape_grokipedia`** — takes a page title and returns structured content from Grokipedia, parsed into sections with headings/blocks plus structured info panels.
- **`search_grokipedia`** — searches Grokipedia for pages matching a query and returns paginated results with titles, snippets, and URLs.

## Notes

- The scraper parses HTML using BeautifulSoup to extract structured Markdown-like sections.
- See `grokipedia_client/client.py` for the scraper implementation.
- See `server.py` for the FastMCP tool definition.
