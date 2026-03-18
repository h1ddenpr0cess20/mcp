# Web MCP Server (FastMCP)

This project provides an MCP server for web search and URL content extraction using **FastMCP** and **SearXNG**.

## Quickstart

```bash
# From the repo root (mcp/)
pip install -r web_mcp/requirements.txt
python web_mcp/server.py
```

SearXNG is installed and started automatically on first run. No API key required.

## Description

The server exposes three tools:

- **`web_search`** — searches the web via SearXNG across multiple engines. Supports all standard search operators and category filters.
- **`news_search`** — convenience wrapper for `web_search` scoped to the news category with a default time range of one week.
- **`fetch_url`** — fetches any URL and returns its content extracted as clean markdown, plain text, or raw HTML.

## Notes

- SearXNG is cloned and installed into `web_mcp/searxng/` on first use. Subsequent starts reuse the existing installation.
- Set `SEARXNG_URL` in the environment to point at an existing SearXNG instance and skip the auto-start.
- See `web_client/` for the search and fetch client implementations.
- See `server.py` for the FastMCP tool definitions.
