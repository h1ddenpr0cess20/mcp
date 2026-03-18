# Configuration

How to install, configure, and connect the Last.fm MCP server to an MCP client such as Claude Desktop.

---

## Table of Contents

- [Requirements](#requirements)
- [Getting a Last.fm API Key](#getting-a-lastfm-api-key)
- [Installation](#installation)
- [Setting Your API Credentials](#setting-your-api-credentials)
- [Running the Server](#running-the-server)
- [Transport Options](#transport-options)
- [Connecting to Claude Desktop](#connecting-to-claude-desktop)
- [Connecting to Other MCP Clients](#connecting-to-other-mcp-clients)

---

## Requirements

- Python 3.9 or later
- A Last.fm account and a free API key (required)
- Internet access (the server calls the Last.fm API at request time)

---

## Getting a Last.fm API Key

A Last.fm API key is required for all read operations. The key is free and can be created in under a minute.

1. Create a Last.fm account at [https://www.last.fm/join](https://www.last.fm/join) if you do not already have one.
2. Go to [https://www.last.fm/api/account/create](https://www.last.fm/api/account/create) and fill out the application form. You can use any name and description — for personal use, something like "My MCP server" is fine.
3. Submit the form. Last.fm will display your **API key** and **Shared Secret** immediately.

Keep these values — you will need them in the next section.

**Which credentials do you need?**

| Credential     | When required                                                      |
|----------------|--------------------------------------------------------------------|
| API key        | Always. Required for every tool in this server.                    |
| API secret     | Only if you use write operations (not currently exposed as tools). |
| Session key    | Only for authenticated write operations (scrobbling, loving tracks). Not needed for read-only use. |

For a read-only setup — browsing artists, charts, tags, and user profiles — only the API key is required.

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
pip install -r lastfm_mcp/requirements.txt
```

---

## Setting Your API Credentials

The server reads credentials from environment variables. There are two ways to provide them.

### Option A — Shell environment variables

Set the variables in your terminal before starting the server.

**macOS and Linux:**

```bash
export LASTFM_API_KEY="your_api_key_here"
export LASTFM_API_SECRET="your_api_secret_here"       # optional, for write operations
export LASTFM_SESSION_KEY="your_session_key_here"      # optional, for authenticated operations
```

**Windows (Command Prompt):**

```cmd
set LASTFM_API_KEY=your_api_key_here
set LASTFM_API_SECRET=your_api_secret_here
set LASTFM_SESSION_KEY=your_session_key_here
```

**Windows (PowerShell):**

```powershell
$env:LASTFM_API_KEY = "your_api_key_here"
$env:LASTFM_API_SECRET = "your_api_secret_here"
$env:LASTFM_SESSION_KEY = "your_session_key_here"
```

Variables set this way only persist for the current terminal session. For a persistent setup, add the `export` lines to your shell profile (e.g. `~/.bash_profile`, `~/.zshrc`).

### Option B — System environment variables (Windows)

On Windows, you can set persistent environment variables through System Properties:

1. Open the Start menu and search for "Edit environment variables for your account."
2. Click "New" under User variables.
3. Add `LASTFM_API_KEY` with your key as the value.
4. Repeat for `LASTFM_API_SECRET` if needed.
5. Restart any open terminals for the changes to take effect.

---

## Running the Server

Once credentials are set and dependencies are installed, start the server:

```bash
python server.py
```

By default, `server.py` runs in stdio mode, which is the correct mode for Claude Desktop and most MCP clients that manage the server process themselves. You should see no output — the server is waiting for a client to connect via stdio.

To run in HTTP mode (useful for testing or persistent setups), edit the bottom of `server.py`:

```python
# Replace this:
mcp.run()

# With this:
mcp.run(transport="http", host="127.0.0.1", port=9201)
```

Then start the server:

```bash
python server.py
```

The server will be available at `http://127.0.0.1:9201/mcp`.

---

## Transport Options

| Transport | How it works                                                   | When to use                                              |
|-----------|----------------------------------------------------------------|----------------------------------------------------------|
| stdio     | Client launches the server as a subprocess and pipes messages  | Claude Desktop and most MCP clients — the default        |
| HTTP      | Client connects to a running HTTP server over a URL            | Persistent setup; multiple clients; easier to debug      |

For Claude Desktop, stdio is the right choice because Claude Desktop starts and stops the server process for you. For a server you want running continuously (on a home machine or a remote host), HTTP is preferable.

---

## Connecting to Claude Desktop

Claude Desktop can connect to MCP servers either by launching them as a subprocess (stdio) or by connecting to an already-running server (HTTP).

### Option A — stdio (Claude Desktop manages the process)

This is the recommended setup. Claude Desktop starts the server when it needs it and stops it when done.

1. Make sure `server.py` uses stdio transport (the default). The bottom of the file should be:

    ```python
    mcp.run()
    ```

2. Find your Claude Desktop configuration file:

    - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
    - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

3. Open the file and add an entry under `mcpServers`. Replace the paths with your actual file system paths:

    ```json
    {
      "mcpServers": {
        "lastfm": {
          "command": "/absolute/path/to/mcp/.venv/bin/python",
          "args": ["/absolute/path/to/mcp/lastfm_mcp/server.py"]
        }
      }
    }
    ```

    On Windows, use the `.venv\Scripts\python.exe` path and backslashes.

4. Save the configuration file and restart Claude Desktop. The Last.fm tools will appear in the tools panel.

**Passing credentials via the config (alternative to .env)**

If you prefer not to use a `.env` file, you can pass the API key through Claude Desktop's environment block:

```json
{
  "mcpServers": {
    "lastfm": {
      "command": "/path/to/mcp/.venv/bin/python",
      "args": ["/path/to/mcp/lastfm_mcp/server.py"],
      "env": {
        "LASTFM_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### Option B — HTTP (connect to a running server)

If you want the server to stay running independently:

1. Edit `server.py` to use HTTP transport:

    ```python
    mcp.run(transport="http", host="127.0.0.1", port=9201)
    ```

2. Start the server:

    ```bash
    python server.py
    ```

3. In `claude_desktop_config.json`, use the `url` key:

    ```json
    {
      "mcpServers": {
        "lastfm": {
          "url": "http://127.0.0.1:9201/mcp"
        }
      }
    }
    ```

4. Save and restart Claude Desktop.

The server must be running before you invoke any Last.fm tools. If Claude Desktop cannot reach the server, the tools will appear unavailable.

---

## Connecting to Other MCP Clients

The server is a standard FastMCP server and works with any MCP-compliant client.

### Generic stdio connection

Any client that launches MCP servers as subprocesses needs:

- **Command:** Full path to the Python interpreter in your virtual environment
- **Arguments:** Full path to `server.py`
- **Environment:** `LASTFM_API_KEY` must be set (either in the system environment, via `.env`, or passed explicitly)

### Generic HTTP connection

With HTTP transport running, any MCP-compliant client can connect to:

```
http://127.0.0.1:9201/mcp
```

Refer to your client's documentation for how to register an MCP server by URL.

### Changing the port

To use a different port, edit `server.py`:

```python
mcp.run(transport="http", host="127.0.0.1", port=9202)
```

Update any client configuration that references the old port.

### Binding to all network interfaces

By default the server binds to `127.0.0.1` (localhost only). To make it reachable on your local network, change the host:

```python
mcp.run(transport="http", host="0.0.0.0", port=9201)
```

Do not expose the server to the public internet. The server has no built-in authentication or rate limiting beyond what the Last.fm API itself enforces.

---

## Last.fm API Rate Limits

Last.fm does not publish explicit rate limits for free API keys, but the general guideline is to avoid making more than 5 requests per second. For normal conversational use through an AI assistant, you are unlikely to approach this limit. If you receive HTTP 429 errors, slow down the request frequency.

Your API key is tied to your Last.fm account. Avoid sharing it publicly or committing it to a public repository.
