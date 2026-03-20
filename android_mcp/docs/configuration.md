# Configuration

How to install, run, and connect the Android MCP server to an MCP client.

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
- [Connecting to Other MCP Clients](#connecting-to-other-mcp-clients)

---

## Requirements

- Python 3.10 or later
- `adb` (Android Debug Bridge) on PATH
- `openssl` on PATH (for auto-generating self-signed TLS certs)
- An Android device with USB debugging enabled, or an emulator running

Verify your device is connected:

```bash
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
pip install -r android_mcp/requirements.txt
```

### Step 4 — Configure

```bash
cp android_mcp/.env.example android_mcp/.env
# Edit .env with your device connection settings
```

---

## Running the Server

```bash
python android_mcp/server.py
```

---

## ADB Connection

### USB (default)

Connect the device via USB with debugging enabled. No `.env` configuration needed — the server auto-detects the device.

### WiFi

First pair over USB:

```bash
adb tcpip 5555
adb connect 192.168.1.x:5555
```

Then set these in `.env`:

| Variable     | Default    | Description |
|--------------|------------|-------------|
| `ADB_HOST`   | *(none)*   | Device IP address |
| `ADB_PORT`   | `5555`     | ADB port |

### Multiple devices

When multiple devices are connected, specify which one to use:

| Variable     | Default    | Description |
|--------------|------------|-------------|
| `ADB_SERIAL` | *(none)*   | Device serial from `adb devices` output |

### Timeout

| Variable      | Default | Description |
|---------------|---------|-------------|
| `ADB_TIMEOUT` | `30`    | Command timeout in seconds |

---

## Screenshots

Screenshots are captured as raw PNG from the device, then compressed using Pillow (resized to max 1024px dimension, JPEG quality 60) to keep file sizes small for vision model analysis.

| Variable         | Default                    | Description |
|------------------|----------------------------|-------------|
| `SCREENSHOT_DIR` | `/tmp/android_screenshots` | Local directory for saved screenshots |

---

## HTTPS File Server

The built-in HTTPS file server serves screenshots and other files so MCP clients can fetch them by URL. Self-signed TLS certificates are generated automatically on first run via `openssl`.

| Variable           | Default                  | Description |
|--------------------|--------------------------|-------------|
| `FILE_SERVER_HOST` | `127.0.0.1`              | Bind address |
| `FILE_SERVER_PORT` | `9701`                   | Port |
| `FILES_DIR`        | `~/mcp-files`            | Local directory for served files |
| `CERT_DIR`         | `~/.android_mcp_certs`   | Directory for auto-generated TLS certs |

Browser-based MCP clients may need to visit `https://127.0.0.1:9701` once in their browser to accept the self-signed certificate before image fetching will work.

---

## Transport Options

The active transport is set in the `__main__` block of `server.py`.

### HTTP (default)

```python
mcp.run(transport="http", host="127.0.0.1", port=9700, path="/mcp")
```

Server listens at `http://127.0.0.1:9700/mcp`.

### stdio

```python
mcp.run()
```

### SSE

```python
mcp.run(transport="sse", host="127.0.0.1", port=9700)
```

| Transport | When to use |
|-----------|-------------|
| stdio     | Clients that manage the server subprocess |
| HTTP      | Persistent server; multiple clients; easiest to debug |
| SSE       | Clients that require SSE transport |

---

## Connecting to an MCP Client

### Option A — stdio

1. Switch `server.py` to stdio transport:

    ```python
    mcp.run()
    ```

2. Add an entry to your client's MCP server config:

    ```json
    {
      "mcpServers": {
        "android": {
          "command": "/absolute/path/to/mcp/.venv/bin/python",
          "args": ["/absolute/path/to/mcp/android_mcp/server.py"]
        }
      }
    }
    ```

3. Restart your MCP client.

### Option B — HTTP

1. Start the server:

    ```bash
    python android_mcp/server.py
    ```

2. Point your client at:

    ```
    http://127.0.0.1:9700/mcp
    ```

---

## Connecting to Other MCP Clients

Any MCP-compliant client can connect via HTTP:

```
http://127.0.0.1:9700/mcp
```

To use a different port, edit `server.py`:

```python
mcp.run(transport="http", host="127.0.0.1", port=9702, path="/mcp")
```

To accept connections from other machines:

```python
mcp.run(transport="http", host="0.0.0.0", port=9700, path="/mcp")
```

Do not expose the server to the public internet without additional authentication.
