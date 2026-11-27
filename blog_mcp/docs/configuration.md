# Configuration

How to install, run, and connect the Blog MCP server to an MCP client.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Server](#running-the-server)
- [Finding the Blog](#finding-the-blog)
- [Transport Options](#transport-options)
- [Connecting to an MCP Client](#connecting-to-an-mcp-client)
- [Connecting to Other MCP Clients](#connecting-to-other-mcp-clients)

---

## Requirements

- Python 3.10 or later
- A running [blog](../../blog/README.md) (this server manages it; it does not host anything itself)

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

### Step 3 — Install dependencies

```bash
pip install -r blog_mcp/requirements.txt
```

### Step 4 — Configure (optional)

```bash
cp blog_mcp/.env.example blog_mcp/.env
```

---

## Running the Server

Start the blog first (`python blog/blog.py`), then:

```bash
python blog_mcp/server.py
```

The blog does not need this server and this server does not host the blog, so you can start and stop them independently.

---

## Finding the Blog

| Variable          | Default                 | Description |
|-------------------|-------------------------|-------------|
| `BLOG_URL`        | `http://127.0.0.1:9901` | Address of the blog |
| `BLOG_API_TOKEN`  | *(from file)*           | The blog's API token |
| `BLOG_DIR`        | `~/mcp-blog`            | Where to look for the token file |
| `BLOG_TIMEOUT`    | `30`                    | Seconds to wait for an answer |
| `BLOG_VERIFY_TLS` | `true`                  | Verify HTTPS certificates |

### Same computer

With the blog's default settings you need no configuration. The blog writes its API token to `~/mcp-blog/api_token`, and this server reads it from there. If you moved the blog's data with `BLOG_DIR`, set the same `BLOG_DIR` here.

### Another machine

```
BLOG_URL=https://blog.example.com
BLOG_API_TOKEN=<the token from the blog's api_token file>
```

Use `https://` so the token is encrypted in transit; the server warns if you use plain `http://` to a non-local address. For a blog with a self-signed certificate, set `BLOG_VERIFY_TLS=false` (this skips certificate checking, so use it only on a network you trust).

The blog's API token is separate from its login password, and it only works for the API.

---

## Transport Options

The active transport is set in the `__main__` block of `server.py`.

### HTTP (default in a terminal)

```python
mcp.run(transport="http", host="127.0.0.1", port=9900, path="/mcp")
```

Server listens at `http://127.0.0.1:9900/mcp`.

### stdio (default when launched by an MCP client)

```python
mcp.run()
```

The server picks stdio automatically when it is not started from an interactive terminal.

### SSE

```python
mcp.run(transport="sse", host="127.0.0.1", port=9900)
```

| Transport | When to use |
|-----------|-------------|
| stdio     | Clients that manage the server subprocess |
| HTTP      | Persistent server; multiple clients; easiest to debug |
| SSE       | Clients that require SSE transport |

---

## Connecting to an MCP Client

### Option A — stdio

Add an entry to your client's MCP server config:

```json
{
  "mcpServers": {
    "blog": {
      "command": "/absolute/path/to/mcp/.venv/bin/python",
      "args": ["/absolute/path/to/mcp/blog_mcp/server.py"]
    }
  }
}
```

Restart your MCP client. If the blog is on another machine, add its settings to the entry:

```json
"env": { "BLOG_URL": "https://blog.example.com", "BLOG_API_TOKEN": "..." }
```

### Option B — HTTP

1. Start the server:

    ```bash
    python blog_mcp/server.py
    ```

2. Point your client at:

    ```
    http://127.0.0.1:9900/mcp
    ```

---

## Connecting to Other MCP Clients

Any MCP-compliant client can connect via HTTP:

```
http://127.0.0.1:9900/mcp
```

To use a different port, edit `server.py`:

```python
mcp.run(transport="http", host="127.0.0.1", port=9902, path="/mcp")
```

To let `subagent_mcp` agents manage the blog, register it there:

```
SUBAGENT_MCP_SERVERS=blog=http://127.0.0.1:9900/mcp
```

The MCP endpoint itself has no authentication, like the other servers in this repo. Anyone who can reach it can use its tools, so keep it on `127.0.0.1` and do not expose it to the internet or an untrusted network.
