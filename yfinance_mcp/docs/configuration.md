# Configuration

How to install, run, and connect the yfinance MCP server to an MCP client such as Claude Desktop.

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
- Internet access (the server fetches data from Yahoo Finance at request time)
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
pip install -r yfinance_mcp/requirements.txt
```

---

## Running the Server

The server supports three transport modes. The active mode is set at the bottom of `server.py`. Only one transport can be active at a time.

### HTTP (default, recommended for most setups)

```bash
python server.py
```

With the default configuration in `server.py`, this starts an HTTP server at:

```
http://127.0.0.1:9301/mcp
```

The server listens only on localhost (`127.0.0.1`), so it is not accessible from other machines on your network unless you change the `host` binding.

### SSE (Server-Sent Events)

To use SSE transport instead, edit the bottom of `server.py`:

```python
# Comment out the HTTP line:
# mcp.run(transport="http", host="127.0.0.1", port=9301, path="/mcp")

# Uncomment the SSE line:
mcp.run(transport="sse", host="127.0.0.1", port=9301)
```

Then start the server normally:

```bash
python server.py
```

### stdio

stdio transport communicates over standard input/output and is used when an MCP client launches the server as a subprocess. You do not run the server manually in this mode — the client starts it. See [Connecting to Claude Desktop](#connecting-to-claude-desktop) for the stdio setup.

To switch to stdio, edit the bottom of `server.py`:

```python
# Comment out other transports and uncomment:
mcp.run()
```

`mcp.run()` with no arguments defaults to stdio.

---

## Transport Options

| Transport | How it works                                                    | When to use                                              |
|-----------|-----------------------------------------------------------------|----------------------------------------------------------|
| HTTP      | Client connects to a running HTTP server over a URL             | Persistent server; multiple clients; easiest to debug    |
| SSE       | Client connects to a running server that streams events         | Clients that require SSE; some older MCP client configs  |
| stdio     | Client launches the server as a subprocess and pipes messages   | Claude Desktop and other clients that manage the process |

For local use with Claude Desktop, stdio is the simplest option because Claude Desktop manages starting and stopping the server process.

For a persistent server you want to keep running (for example, on a home server or a cloud VM), HTTP is the better choice.

---

## Connecting to Claude Desktop

Claude Desktop can connect to MCP servers in two ways: by launching them as a subprocess (stdio) or by connecting to an already-running server (HTTP/SSE).

### Option A — stdio (Claude Desktop manages the process)

1. Switch `server.py` to stdio transport by editing the bottom of the file:

    ```python
    mcp.run()
    ```

2. Find your Claude Desktop configuration file:

    - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
    - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

3. Add an entry under `mcpServers`. Replace the paths with your actual paths:

    ```json
    {
      "mcpServers": {
        "yfinance": {
          "command": "/absolute/path/to/mcp/.venv/bin/python",
          "args": ["/absolute/path/to/mcp/yfinance_mcp/server.py"]
        }
      }
    }
    ```

    On Windows, use the `.venv\Scripts\python.exe` path and backslashes.

4. Save the file and restart Claude Desktop. The yfinance tools will appear in the tools panel.

### Option B — HTTP (connect to a running server)

If you prefer to keep the server running independently (so it is available without restarting Claude Desktop):

1. Start the server in HTTP mode:

    ```bash
    python server.py
    ```

2. In `claude_desktop_config.json`, use the `url` key:

    ```json
    {
      "mcpServers": {
        "yfinance": {
          "url": "http://127.0.0.1:9301/mcp"
        }
      }
    }
    ```

3. Save and restart Claude Desktop.

The server must be running before you open Claude Desktop (or before you invoke a tool). Claude Desktop will show the tools as unavailable if the server is not reachable.

---

## Connecting to Other MCP Clients

The server is a standard FastMCP server and works with any MCP-compliant client.

### Generic HTTP connection

Any client that supports MCP over HTTP can connect to:

```
http://127.0.0.1:9301/mcp
```

Refer to your client's documentation for how to register an MCP server URL.

### Generic stdio connection

Any client that supports launching MCP servers as subprocesses needs:

- **Command:** full path to the Python interpreter in your virtual environment
- **Arguments:** full path to `server.py`
- **Working directory:** the `mcp/yfinance_mcp` folder (optional but recommended)

### Changing the port

To use a different port, edit the `port` argument in `server.py`:

```python
mcp.run(transport="http", host="127.0.0.1", port=9302, path="/mcp")
```

Then update any client configuration that references the old port number.

### Binding to all interfaces

By default, the server binds to `127.0.0.1` (localhost only). To make it accessible on your local network, change the host to `0.0.0.0`:

```python
mcp.run(transport="http", host="0.0.0.0", port=9301, path="/mcp")
```

Do not expose the server to the public internet without additional authentication. The server has no built-in access controls.
