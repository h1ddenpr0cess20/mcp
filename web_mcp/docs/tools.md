# Tool Reference

Complete reference for all tools exposed by the Web MCP server.

---

## Table of Contents

- [web\_search](#web_search)
- [news\_search](#news_search)
- [fetch\_url](#fetch_url)
- [Return Value Structure](#return-value-structure)
- [Error Handling](#error-handling)

---

## web\_search

Searches the web using a local SearXNG instance, which queries multiple search engines simultaneously (DuckDuckGo, Brave, Startpage, and others). Results are ranked and deduplicated by SearXNG before being returned.

**Parameters**

| Parameter   | Type    | Required | Default | Description |
|-------------|---------|----------|---------|-------------|
| query       | string  | yes      | —       | Search query. Supports operators like `site:`, `intitle:`, `inurl:`, `"exact phrase"`, `-exclude`. |
| categories  | string  | no       | null    | Comma-separated category filter: `general`, `images`, `news`, `videos`, `music`, `files`, `it`, `science`, `social media`, `map`. |
| language    | string  | no       | `"en"`  | Language code, e.g. `"en"`, `"fr"`, `"de"`. |
| time_range  | string  | no       | null    | Restrict results by age: `"day"`, `"week"`, `"month"`, `"year"`. |
| max_results | integer | no       | `10`    | Maximum number of results to return. |
| engines     | string  | no       | null    | Comma-separated list of specific engines to query, e.g. `"google,bing"`. |
| safesearch  | integer | no       | `0`     | Safe search level: `0` = off, `1` = moderate, `2` = strict. |
| pageno      | integer | no       | `1`     | Page number for pagination. |

**Returns**

A list of result objects. Each object contains:

| Field         | Type    | Description |
|---------------|---------|-------------|
| title         | string  | Page title |
| url           | string  | Page URL |
| content       | string  | Short excerpt or description |
| engine        | string  | The engine that returned this result |
| engines       | list    | All engines that returned this result |
| score         | number  | Relevance score assigned by SearXNG |
| publishedDate | string or null | Publication date if available |

**Use cases**

- General web research with optional engine and category filtering.
- Targeted queries using Google-style operators (`site:github.com fastmcp`).
- Time-filtered searches for recent content.

---

## news\_search

Searches for recent news articles. Equivalent to calling `web_search` with `categories="news"`. Defaults to results from the past week.

**Parameters**

| Parameter   | Type    | Required | Default   | Description |
|-------------|---------|----------|-----------|-------------|
| query       | string  | yes      | —         | News search query. |
| language    | string  | no       | `"en"`    | Language code. |
| time_range  | string  | no       | `"week"`  | Time filter: `"day"`, `"week"`, `"month"`, `"year"`. |
| max_results | integer | no       | `10`      | Maximum number of results to return. |

**Returns**

Same structure as `web_search`. News results typically include a populated `publishedDate` field.

**Use cases**

- Find recent news on a topic without specifying the news category manually.
- Monitor recent coverage of a person, company, or event.

---

## fetch\_url

Fetches the content of a URL and extracts readable text. Uses trafilatura for main-content extraction (strips navigation, ads, footers) with markdownify as a fallback for pages where extraction fails.

**Parameters**

| Parameter     | Type    | Required | Default      | Description |
|---------------|---------|----------|--------------|-------------|
| url           | string  | yes      | —            | The URL to fetch. |
| output_format | string  | no       | `"markdown"` | Output format: `"markdown"`, `"text"`, or `"html"`. |
| include_links | boolean | no       | `true`       | Whether to include hyperlinks in the extracted content. |

**Returns**

A dictionary with the following keys:

| Key     | Type   | Description |
|---------|--------|-------------|
| url     | string | The URL that was fetched (after redirects) |
| title   | string | Page title if extracted, otherwise empty string |
| content | string | Extracted page content in the requested format |

**Output formats**

| Format     | Description |
|------------|-------------|
| `markdown` | Main article content converted to Markdown. Best for reading and summarisation. |
| `text`     | Plain text extraction. No markup. |
| `html`     | Raw HTML as returned by the server. |

**Use cases**

- Read the full content of a URL returned by `web_search`.
- Extract article text for summarisation or question answering.
- Retrieve raw HTML for scraping or analysis.

---

## Return Value Structure

### Search result object

```json
{
  "title": "FastMCP documentation",
  "url": "https://gofastmcp.com/",
  "content": "FastMCP is a framework for building MCP servers in Python.",
  "engine": "brave",
  "engines": ["brave", "duckduckgo"],
  "score": 4.5,
  "publishedDate": null
}
```

### Fetch result object

```json
{
  "url": "https://example.com/article",
  "title": "Example Article",
  "content": "# Example Article\n\nThis is the article body..."
}
```

---

## Error Handling

Both search tools raise `httpx.HTTPStatusError` on non-2xx responses from SearXNG. The `fetch_url` tool raises `httpx.HTTPStatusError` on non-2xx responses from the target URL and `httpx.ConnectError` if the host is unreachable.

Errors propagate to the MCP client as tool execution errors rather than structured error dictionaries.
