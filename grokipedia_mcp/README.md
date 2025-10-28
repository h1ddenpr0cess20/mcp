# Grokipedia MCP Server (FastMCP)

This project provides an MCP server for scraping Grokipedia pages using **FastMCP**.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python server.py  # runs an MCP server; see FastMCP docs for client hookup
```

## Description

The server exposes a single tool `scrape_grokipedia` that takes a page title and returns structured content from Grokipedia, parsed into sections with headings and blocks of text.

## Notes

- The scraper parses HTML using BeautifulSoup to extract structured Markdown-like sections.
- See `grokipedia_client/client.py` for the scraper implementation.
- See `server.py` for the FastMCP tool definition.
