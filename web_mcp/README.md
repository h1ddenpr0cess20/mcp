# Web MCP Server (FastMCP)

This project provides an MCP server for web search and URL content extraction using **FastMCP** and **SearXNG**.

## Quickstart

```bash
# From the repo root (mcp/)
pip install -r web_mcp/requirements.txt
playwright install chromium
python web_mcp/server.py
```

SearXNG is installed and started automatically on first run. No API key required.

## Tools

- **`web_search`** — searches the web via SearXNG across multiple engines. Supports all standard search operators and category filters.
- **`news_search`** — convenience wrapper for `web_search` scoped to the news category with a default time range of one week.
- **`fetch_url`** — fetches any URL and returns its content extracted as clean markdown, plain text, or raw HTML. Uses `curl_cffi` with Chrome TLS impersonation to avoid bot detection, with automatic Playwright headless browser fallback for JS-rendered pages.

## Configuration

Configuration is done via environment variables. Copy `.env.example` to `.env` and uncomment as needed.

| Variable | Default | Description |
|---|---|---|
| `SEARXNG_URL` | *(auto-start local)* | URL of an existing SearXNG instance |
| `SEARXNG_TIMEOUT` | `30` | SearXNG request timeout (seconds) |
| `FETCH_TIMEOUT` | `30` | URL fetch timeout (seconds) |
| `FETCH_PROXIES` | *(none)* | Comma-separated proxy URLs, rotated randomly per request |

### Proxy support

Set `FETCH_PROXIES` to one or more proxy URLs (comma-separated). Supports HTTP, HTTPS, and SOCKS5, with optional authentication:

```
FETCH_PROXIES=http://host:port,socks5://user:pass@host:port
```

Proxies are used by both the `curl_cffi` fast path and the Playwright JS fallback.

## Notes

- SearXNG is cloned and installed into `web_mcp/searxng/` on first use. Subsequent starts reuse the existing installation.
- The fetcher tries `curl_cffi` (Chrome TLS fingerprint) first, then falls back to a headless Chromium browser for JS-heavy pages.
- See `web_client/` for the search and fetch client implementations.
- See `server.py` for the FastMCP tool definitions.
