# Configuration

How to install, run, and connect the Fire TV MCP server to an MCP client.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Server](#running-the-server)
- [ADB Connection](#adb-connection)
- [Screenshots](#screenshots)
- [HTTPS File Server](#https-file-server)
- [Transport Options](#transport-options)
- [Connecting to an MCP Client](#connecting-to-an-mcp-client)

---

## Requirements

- Python 3.10 or later
- `adb` (Android Debug Bridge) on PATH
- `openssl` on PATH (for auto-generating self-signed TLS certs)
- ADB debugging enabled on the Fire TV

Enable ADB on your Fire TV:

1. Settings → My Fire TV → About → click Build Version 7 times to enable Developer Options
2. Settings → My Fire TV → Developer Options → ADB Debugging → ON
3. Settings → My Fire TV → Developer Options → Apps from Unknown Sources → ON (for sideloading)

Verify your device is connected:

```bash
adb connect <firetv-ip>:5555
adb devices
```

---

## Installation

### Step 1 — Clone the monorepo

```bash
git clone https://github.com/h1ddenpr0cess20/mcp.git
cd mcp
```

### Step 2 — Create and activate the virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r firetv_mcp/requirements.txt
```

### Step 4 — Configure

```bash
cp firetv_mcp/.env.example firetv_mcp/.env
# Edit .env with your Fire TV IP address
```

---

## Running the Server

```bash
python firetv_mcp/server.py
```

---

## ADB Connection

### WiFi (default for Fire TV)

Set these in `.env`:

| Variable | Default | Description |
|---|---|---|
| `FIRETV_HOST` | *(none)* | Fire TV IP address |
| `FIRETV_PORT` | `5555` | ADB port |

Fallback variables `ADB_HOST` / `ADB_PORT` are also supported.

### Multiple devices

When multiple devices are connected, specify which one to use:

| Variable | Default | Description |
|---|---|---|
| `ADB_SERIAL` | *(none)* | Device serial from `adb devices` output |

### Timeout

| Variable | Default | Description |
|---|---|---|
| `ADB_TIMEOUT` | `10` | Command timeout in seconds |

---

## Screenshots

Screenshots are captured as raw PNG from the Fire TV, then compressed using Pillow (resized to max 1024px dimension, JPEG quality 60) to keep file sizes small for vision model analysis.

| Variable | Default | Description |
|---|---|---|
| `SCREENSHOT_DIR` | `/tmp/firetv_screenshots` | Local directory for saved screenshots |

---

## HTTPS File Server

The built-in HTTPS file server serves screenshots and other files so MCP clients can fetch them by URL. Self-signed TLS certificates are generated automatically on first run via `openssl`.

| Variable | Default | Description |
|---|---|---|
| `FILE_SERVER_HOST` | `127.0.0.1` | Bind address |
| `FILE_SERVER_PORT` | `9815` | Port |
| `FILES_DIR` | `~/firetv-mcp-files` | Local directory for served files |
| `CERT_DIR` | `~/.firetv_mcp_certs` | Directory for auto-generated TLS certs |

---

## Transport Options

The server auto-detects transport based on whether stdin is a TTY.

### HTTP (default when launched directly)

```python
mcp.run(transport="http", host="127.0.0.1", port=9814, path="/mcp")
```

Server listens at `http://127.0.0.1:9814/mcp`.

### stdio (when launched by an MCP client)

```python
mcp.run()
```

| Transport | When to use |
|---|---|
| stdio | Clients that manage the server subprocess |
| HTTP | Persistent server; multiple clients; easiest to debug |

---

## Connecting to an MCP Client

### Option A — stdio

Add an entry to your client's MCP server config:

```json
{
  "mcpServers": {
    "firetv": {
      "command": "/absolute/path/to/mcp/.venv/bin/python",
      "args": ["/absolute/path/to/mcp/firetv_mcp/server.py"]
    }
  }
}
```

### Option B — HTTP

Start the server:

```bash
python firetv_mcp/server.py
```

Point your client at:

```
http://127.0.0.1:9814/mcp
```

To accept connections from other machines:

```python
mcp.run(transport="http", host="0.0.0.0", port=9814, path="/mcp")
```

Do not expose the server to the public internet without additional authentication.
