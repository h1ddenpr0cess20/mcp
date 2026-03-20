# Configuration

How to install, run, and connect the Web MCP server to an MCP client such as Claude Desktop.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Server](#running-the-server)
- [SearXNG](#searxng)
- [Transport Options](#transport-options)
- [Connecting to Claude Desktop](#connecting-to-claude-desktop)
- [Connecting to Other MCP Clients](#connecting-to-other-mcp-clients)

---

## Requirements

- Python 3.10 or later
- `git` available on `PATH` (used to clone SearXNG on first run)
- Internet access
- No API key required

---

## Installation

### Step 1 — Clone the monorepo

```bash
git clone https://github.com/h1ddenpr0cess20/mcp.git
cd mcp
```

### Step 2 — Create and activate the virtual environment

**macOS and Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (Command Prompt):**

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Step 3 — Install dependencies

```bash
pip install -r web_mcp/requirements.txt
```

---

## Running the Server

```bash
python web_mcp/server.py
```

On first run, the server will clone SearXNG from GitHub and install it into `web_mcp/searxng/`. This takes a minute or two. Subsequent starts skip installation and launch immediately.

---

## SearXNG

The server manages a local SearXNG instance automatically. SearXNG is the search backend — it queries multiple engines (DuckDuckGo, Brave, Startpage, Wikipedia, and others) and returns merged results.

**Auto-managed (default)**

SearXNG is cloned to `web_mcp/searxng/searxng-src/`, installed into the active Python environment, and started as a subprocess on port `8888`. It is shut down when the MCP server process exits.

Configuration is read from `web_mcp/searxng/settings.yml`. The defaults enable JSON API access with no rate limiting.

**External instance**

To use an existing SearXNG instance instead of the auto-managed one, set the `SEARXNG_URL` environment variable before starting the server:

```bash
SEARXNG_URL=http://192.168.1.10:8080 python web_mcp/server.py
```

When `SEARXNG_URL` is set, the server connects to that instance directly and does not start a local one.

**Environment variables**

| Variable       | Default                 | Description |
|----------------|-------------------------|-------------|
| `SEARXNG_URL`  | `http://127.0.0.1:8888` | URL of the SearXNG instance to use. Set to skip auto-start. |
| `SEARXNG_TIMEOUT` | `30`                | Timeout in seconds for search requests. |
| `FETCH_TIMEOUT`   | `30`                | Timeout in seconds for URL fetch requests. |

---

## Transport Options

The active transport is controlled by the `mcp.run()` call at the bottom of `server.py`.

### stdio (default commented out)

```python
mcp.run()
```

```bash
python server.py
```

### HTTP (default active)

```python
mcp.run(transport="http", host="127.0.0.1", port=9510, path="/mcp")
```

```bash
python server.py
```

The server listens at:

```
http://127.0.0.1:9510/mcp
```

### SSE

```python
mcp.run(transport="sse", host="127.0.0.1", port=9510)
```

| Transport | When to use |
|-----------|-------------|
| stdio     | Claude Desktop and clients that manage the subprocess |
| HTTP      | Persistent server; multiple clients; easiest to debug |
| SSE       | Clients that require SSE transport |

---

## Connecting to Claude Desktop

### Option A — stdio

1. Switch `server.py` to stdio transport:

    ```python
    mcp.run()
    ```

2. Find the Claude Desktop config:
    - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
    - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

3. Add an entry under `mcpServers`:

    ```json
    {
      "mcpServers": {
        "web": {
          "command": "/absolute/path/to/mcp/.venv/bin/python",
          "args": ["/absolute/path/to/mcp/web_mcp/server.py"]
        }
      }
    }
    ```

4. Save and restart Claude Desktop.

### Option B — HTTP

1. Start the server with HTTP transport:

    ```bash
    python web_mcp/server.py
    ```

2. In `claude_desktop_config.json`:

    ```json
    {
      "mcpServers": {
        "web": {
          "url": "http://127.0.0.1:9510/mcp"
        }
      }
    }
    ```

3. Save and restart Claude Desktop.

---

## Connecting to Other MCP Clients

Any MCP-compliant client can connect via HTTP:

```
http://127.0.0.1:9510/mcp
```

To use a different port, edit `server.py`:

```python
mcp.run(transport="http", host="127.0.0.1", port=9512, path="/mcp")
```

To accept connections from other machines on your network:

```python
mcp.run(transport="http", host="0.0.0.0", port=9510, path="/mcp")
```

Do not expose the server to the public internet without additional authentication.
