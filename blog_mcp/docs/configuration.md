# Configuration

How to install, run, and connect the Blog MCP server to an MCP client.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Server](#running-the-server)
- [Storage](#storage)
- [Viewer Login](#viewer-login)
- [Remote Access and HTTPS](#remote-access-and-https)
- [Transport Options](#transport-options)
- [Connecting to an MCP Client](#connecting-to-an-mcp-client)
- [Connecting to Other MCP Clients](#connecting-to-other-mcp-clients)
- [Backups](#backups)

---

## Requirements

- Python 3.10 or later
- No API keys, accounts, or external services

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
# Edit .env to set the blog title, port, or password
```

---

## Running the Server

```bash
python blog_mcp/server.py
```

On startup the server prints the viewer address and where the password is kept:

```
[blog] viewer: http://127.0.0.1:9411  (user: owner, password: /home/you/mcp-blog/viewer_password)
```

---

## Storage

| Variable   | Default      | Description |
|------------|--------------|-------------|
| `BLOG_DIR` | `~/mcp-blog` | Directory holding the blog |

The directory contains:

| File              | Description |
|-------------------|-------------|
| `blog.db`         | SQLite database with every post, tag, and timestamp |
| `viewer_password` | Generated viewer password (only when `BLOG_PASSWORD` is unset) |

If the directory does not exist it is created with mode `0700`, and `blog.db` and `viewer_password` are created with mode `0600`. A directory that already exists is left as it is, so pointing `BLOG_DIR` at a shared folder does not change its permissions.

Limits: titles up to 200 characters, summaries up to 500, bodies up to 1,000,000, and up to 20 tags per post (50 characters each).

---

## Viewer Login

| Variable           | Default       | Description |
|--------------------|---------------|-------------|
| `BLOG_TITLE`       | `Private Blog` | Blog name |
| `BLOG_DESCRIPTION` | *(empty)*     | Tagline |
| `BLOG_USERNAME`    | `owner`       | Login name (must not contain `:`) |
| `BLOG_PASSWORD`    | *(generated)* | Login password |

When `BLOG_PASSWORD` is unset, the server generates a random password the first time it runs and keeps it in `$BLOG_DIR/viewer_password`. The same password is reused on later starts. To change it, edit or delete that file and restart; deleting it generates a new one.

When `BLOG_PASSWORD` is set, nothing is written to disk. Keep `.env` out of version control (the repo's `.gitignore` already excludes it).

The viewer never starts without a password.

---

## Remote Access and HTTPS

| Variable                       | Default     | Description |
|--------------------------------|-------------|-------------|
| `BLOG_HOST`                    | `127.0.0.1` | Bind address |
| `BLOG_PORT`                    | `9411`      | Port |
| `BLOG_TLS_CERT`, `BLOG_TLS_KEY` | *(none)*   | PEM files; set both to serve HTTPS |

HTTP Basic authentication sends the password with every request, so on any network other than loopback it must travel over HTTPS. To read the blog from your phone or another computer:

```bash
# Self-signed certificate valid for one year (your browser will ask you to trust it once)
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout ~/mcp-blog/blog.key -out ~/mcp-blog/blog.pem -subj "/CN=blog"
```

```
BLOG_HOST=0.0.0.0
BLOG_TLS_CERT=~/mcp-blog/blog.pem
BLOG_TLS_KEY=~/mcp-blog/blog.key
```

If you bind a non-loopback address without a certificate, the server still starts but prints a warning. Another option is to keep the viewer on loopback and reach it through an SSH tunnel or a VPN you already trust.

Only the viewer is affected by these settings. The MCP endpoint (port 9410) stays on `127.0.0.1` and is not password-protected; do not expose it.

---

## Transport Options

The active transport is set in the `__main__` block of `server.py`. The viewer runs in the same process whichever transport you pick.

### HTTP (default in a terminal)

```python
mcp.run(transport="http", host="127.0.0.1", port=9410, path="/mcp")
```

Server listens at `http://127.0.0.1:9410/mcp`.

### stdio (default when launched by an MCP client)

```python
mcp.run()
```

The server picks stdio automatically when it is not started from an interactive terminal. Startup messages go to stderr, so they never interfere with the protocol.

### SSE

```python
mcp.run(transport="sse", host="127.0.0.1", port=9410)
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

Restart your MCP client. The viewer starts together with the server and stops when the client closes it.

### Option B — HTTP

1. Start the server:

    ```bash
    python blog_mcp/server.py
    ```

2. Point your client at:

    ```
    http://127.0.0.1:9410/mcp
    ```

---

## Connecting to Other MCP Clients

Any MCP-compliant client can connect via HTTP:

```
http://127.0.0.1:9410/mcp
```

To use a different port, edit `server.py`:

```python
mcp.run(transport="http", host="127.0.0.1", port=9412, path="/mcp")
```

To let other `subagent_mcp` agents write to the blog, register it there:

```
SUBAGENT_MCP_SERVERS=blog=http://127.0.0.1:9410/mcp
```

Do not expose the MCP port to the public internet or an untrusted network.

---

## Backups

Everything lives in `BLOG_DIR`. To back up, copy `blog.db` while the server is idle, or use SQLite's own tool, which is safe at any time:

```bash
sqlite3 ~/mcp-blog/blog.db ".backup '$HOME/blog-backup.db'"
```

To restore, stop the server and put the file back as `blog.db`.
