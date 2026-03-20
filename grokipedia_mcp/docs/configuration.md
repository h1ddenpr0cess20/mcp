# Configuration

How to install, run, and connect the Grokipedia MCP server to an MCP client such as Claude Desktop.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Server](#running-the-server)
- [Transport Options](#transport-options)
- [Connecting to Claude Desktop](#connecting-to-claude-desktop)
- [Connecting to Other MCP Clients](#connecting-to-other-mcp-clients)

---

## Requirements

- Python 3.9 or later
- Internet access (the server fetches pages from Grokipedia at request time)
- No API key required

---

## Installation

### Step 1 — Clone the monorepo

This server lives inside the [mcp](https://github.com/h1ddenpr0cess20/mcp) monorepo alongside other MCP servers.

```bash
git clone https://github.com/h1ddenpr0cess20/mcp.git
cd mcp
```

### Step 2 — Create and activate the virtual environment

The monorepo uses a single shared virtual environment at the repo root.

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

With the virtual environment activated:

```bash
pip install -r grokipedia_mcp/requirements.txt
```

---

## Running the Server

The server supports three transport modes. The active mode is controlled by the `mcp.run()` call at the bottom of `server.py`.

### stdio (default)

The default configuration runs the server over stdio:

```bash
python server.py
```

In stdio mode, the server communicates over standard input/output. You do not interact with it directly in the terminal — instead, an MCP client (such as Claude Desktop) launches the server as a subprocess and communicates with it automatically. See [Connecting to Claude Desktop](#connecting-to-claude-desktop).

### HTTP

To run as a persistent HTTP server, edit the bottom of `server.py`:

```python
# Comment out the stdio line:
# mcp.run()

# Uncomment the HTTP line:
mcp.run(transport="http", host="127.0.0.1", port=9110, path="/mcp")
```

Then start the server:

```bash
python server.py
```

The server will listen at:

```
http://127.0.0.1:9110/mcp
```

The server binds to localhost only (`127.0.0.1`), so it is not accessible from other machines on your network unless you change the `host` binding.

### SSE (Server-Sent Events)

To use SSE transport, edit the bottom of `server.py`:

```python
# Comment out other transports:
# mcp.run()
# mcp.run(transport="http", host="127.0.0.1", port=9110, path="/mcp")

# Uncomment the SSE line:
mcp.run(transport="sse", host="127.0.0.1", port=9110)
```

Then start the server:

```bash
python server.py
```

---

## Transport Options

| Transport | How it works                                                    | When to use                                              |
|-----------|-----------------------------------------------------------------|----------------------------------------------------------|
| stdio     | Client launches the server as a subprocess and pipes messages   | Claude Desktop and other clients that manage the process |
| HTTP      | Client connects to a running HTTP server over a URL             | Persistent server; multiple clients; easiest to debug    |
| SSE       | Client connects to a running server that streams events         | Clients that require SSE; some older MCP client configs  |

For local use with Claude Desktop, stdio is the simplest option because Claude Desktop manages starting and stopping the server process automatically.

For a persistent server you want to keep running independently, HTTP is the better choice.

---

## Connecting to Claude Desktop

Claude Desktop can connect to MCP servers in two ways: by launching them as a subprocess (stdio) or by connecting to an already-running server (HTTP/SSE).

### Option A — stdio (Claude Desktop manages the process)

1. Confirm `server.py` is using stdio transport (this is the default). The bottom of the file should read:

    ```python
    mcp.run()
    ```

2. Find your Claude Desktop configuration file:

    - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
    - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

3. Add an entry under `mcpServers`. Replace the paths with your actual absolute paths:

    ```json
    {
      "mcpServers": {
        "grokipedia": {
          "command": "/absolute/path/to/mcp/.venv/bin/python",
          "args": ["/absolute/path/to/mcp/grokipedia_mcp/server.py"]
        }
      }
    }
    ```

    On Windows, use the `.venv\Scripts\python.exe` path and backslashes.

4. Save the file and restart Claude Desktop. The `scrape_grokipedia` tool will appear in the tools panel.

### Option B — HTTP (connect to a running server)

If you prefer to keep the server running independently:

1. Switch `server.py` to HTTP transport and start it:

    ```bash
    python server.py
    ```

2. In `claude_desktop_config.json`, use the `url` key:

    ```json
    {
      "mcpServers": {
        "grokipedia": {
          "url": "http://127.0.0.1:9110/mcp"
        }
      }
    }
    ```

3. Save and restart Claude Desktop.

The server must be running before you open Claude Desktop or invoke a tool. If the server is not reachable, Claude Desktop will show the tools as unavailable.

---

## Connecting to Other MCP Clients

The server is a standard FastMCP server and works with any MCP-compliant client.

### Generic HTTP connection

Any client that supports MCP over HTTP can connect to:

```
http://127.0.0.1:9110/mcp
```

Refer to your client's documentation for how to register an MCP server URL.

### Generic stdio connection

Any client that supports launching MCP servers as subprocesses needs:

- **Command:** full path to the Python interpreter in your virtual environment
- **Arguments:** full path to `server.py`
- **Working directory:** the `mcp/grokipedia_mcp` folder (optional but recommended)

### Changing the port

To use a different port, edit the `port` argument in `server.py`:

```python
mcp.run(transport="http", host="127.0.0.1", port=9112, path="/mcp")
```

Then update any client configuration that references the old port number.

### Binding to all interfaces

By default, the server binds to `127.0.0.1` (localhost only). To make it accessible on your local network, change the host to `0.0.0.0`:

```python
mcp.run(transport="http", host="0.0.0.0", port=9110, path="/mcp")
```

Do not expose the server to the public internet without additional authentication. The server has no built-in access controls.
