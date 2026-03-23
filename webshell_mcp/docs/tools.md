# Tool Reference

Complete reference for all tools exposed by the WebShell MCP server.

---

## Table of Contents

- [execute\_command](#execute_command)
- [list\_directory](#list_directory)
- [read\_file](#read_file)
- [write\_file](#write_file)
- [upload\_file](#upload_file)
- [download\_file](#download_file)
- [get\_system\_info](#get_system_info)
- [fetch\_file](#fetch_file)
- [web\_search](#web_search)
- [news\_search](#news_search)
- [fetch\_url](#fetch_url)
- [Return Value Structure](#return-value-structure)
- [Error Handling](#error-handling)

---

## execute\_command

Executes a shell command in the sandbox and returns its output.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| command   | string | yes      | Shell command to execute. Supports pipes, redirects, and multi-statement commands. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output from the command |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success) |

**Use cases**

- Run arbitrary shell commands, scripts, or programs in the sandbox.
- Install packages, compile code, or manage services.
- Inspect logs, processes, or system state.

---

## list\_directory

Lists the contents of a directory in the sandbox.

**Parameters**

| Parameter | Type   | Required | Default | Description |
|-----------|--------|----------|---------|-------------|
| path      | string | no       | `"~"`   | Directory path in the sandbox. Supports `~` and `~/subdir` expansion. |

**Returns**

A list of entry objects. Each object contains:

| Field       | Type    | Description |
|-------------|---------|-------------|
| name        | string  | File or directory name |
| size        | integer | Size in bytes |
| is_dir      | boolean | `true` if the entry is a directory |
| permissions | string  | Octal permission string, e.g. `"0o755"` |
| modified    | number  | Last-modified time as a Unix timestamp |

---

## read\_file

Reads the contents of a file in the sandbox and returns them as a string.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| path      | string | yes      | Absolute path to the file in the sandbox. |

**Returns**

The file contents as a plain string.

---

## write\_file

Writes content to a file in the sandbox. Creates the file if it does not exist; overwrites it if it does.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| path      | string | yes      | Absolute destination path in the sandbox. |
| content   | string | yes      | Content to write. |

**Returns**

| Field | Type    | Description |
|-------|---------|-------------|
| path  | string  | Resolved absolute path of the written file |
| size  | integer | Size of the written file in bytes |

---

## upload\_file

Uploads a file from the local machine into the sandbox via SFTP.

**Parameters**

| Parameter   | Type   | Required | Description |
|-------------|--------|----------|-------------|
| local_path  | string | yes      | Path to the file on the local machine. |
| remote_path | string | yes      | Destination path in the sandbox. |

**Returns**

| Field       | Type    | Description |
|-------------|---------|-------------|
| remote_path | string  | Destination path in the sandbox |
| size        | integer | Size of the uploaded file in bytes |

---

## download\_file

Downloads a file from the sandbox to the local machine via SFTP.

**Parameters**

| Parameter   | Type   | Required | Description |
|-------------|--------|----------|-------------|
| remote_path | string | yes      | Path to the file in the sandbox. |
| local_path  | string | yes      | Destination path on the local machine. |

**Returns**

| Field      | Type    | Description |
|------------|---------|-------------|
| local_path | string  | Destination path on the local machine |
| size       | integer | Size of the downloaded file in bytes |

---

## get\_system\_info

Returns basic system information from the sandbox.

**Parameters**

None.

**Returns**

| Field          | Type   | Description |
|----------------|--------|-------------|
| hostname       | string | Sandbox hostname |
| uptime         | string | Human-readable uptime, e.g. `"up 2 hours, 14 minutes"` |
| kernel         | string | Kernel version string |
| mem_total      | string | Total memory, e.g. `"3.8Gi"` |
| mem_used       | string | Used memory |
| mem_available  | string | Available memory |
| disk_total     | string | Total disk size on `/` |
| disk_used      | string | Used disk space |
| disk_available | string | Available disk space |
| disk_use_pct   | string | Disk usage percentage, e.g. `"42%"` |

On command failure, returns the raw stdout/stderr/exit_code dict instead.

---

## fetch\_file

Downloads a file from the sandbox and makes it available via a local HTTP URL. Useful for retrieving generated documents, archives, images, or any binary file so the client can download it directly.

**Parameters**

| Parameter   | Type   | Required | Description |
|-------------|--------|----------|-------------|
| remote_path | string | yes      | Absolute path to the file in the sandbox. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| file_id   | string  | Unique identifier for the file |
| url       | string  | Local HTTP URL where the file can be downloaded |
| filename  | string  | Filename extracted from the path |
| size      | integer | File size in bytes |
| mime_type | string  | MIME type inferred from the filename, e.g. `"application/pdf"` |

Files are saved to `~/mcp-files/` and served on `http://127.0.0.1:9712/` by default.

---

## web\_search

Searches the web using SearXNG running inside the VM, which queries multiple search engines simultaneously (DuckDuckGo, Brave, Startpage, and others). Results are ranked and deduplicated by SearXNG before being returned.

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

Fetches the content of a URL and extracts readable text. All fetching happens inside the VM: uses curl_cffi with Chrome TLS impersonation first, then falls back to a headless Chromium browser (Playwright) for JS-rendered pages. Content is extracted with trafilatura, with markdownify as a fallback.

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

### execute\_command

```json
{
  "stdout": "Hello, world!\n",
  "stderr": "",
  "exit_code": 0
}
```

### list\_directory entry

```json
{
  "name": "report.pdf",
  "size": 204800,
  "is_dir": false,
  "permissions": "0o644",
  "modified": 1710000000.0
}
```

### fetch\_file

```json
{
  "file_id": "file_a1b2c3d4e5f67890",
  "url": "http://127.0.0.1:9712/files/file_a1b2c3d4e5f67890/content",
  "filename": "report.pdf",
  "size": 204800,
  "mime_type": "application/pdf"
}
```

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

All tools propagate exceptions directly to the MCP client as tool execution errors rather than returning structured error dictionaries (except `get_system_info`, which returns the raw command result on failure).

Common errors:

- `paramiko.ssh_exception.NoValidConnectionsError` — SSH host unreachable or wrong port.
- `paramiko.AuthenticationException` — SSH authentication failed (bad key or password).
- `FileNotFoundError` / `IOError` — SFTP operation on a path that does not exist.
- `socket.timeout` — Command exceeded `COMMAND_TIMEOUT` (default 30s).
- `httpx.HTTPStatusError` — Non-2xx response from SearXNG (search tools).
- `fetch_url` errors are returned as `{"url": ..., "title": "", "content": "Error: ..."}` rather than raising exceptions, since the fetch script runs remotely.
