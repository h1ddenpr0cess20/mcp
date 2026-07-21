# Configuration

How to install, run, and connect the Colab Shell MCP server to an MCP client.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Backends](#backends)
- [Running the Server](#running-the-server)
- [Running the Bridge in Colab](#running-the-bridge-in-colab)
- [Environment Variables](#environment-variables)
- [File Server](#file-server)
- [Transport Options](#transport-options)
- [Connecting to an MCP Client](#connecting-to-an-mcp-client)
- [Note on browser reachability checks](#note-on-browser-reachability-checks)

---

## Requirements

- Python 3.10 or later
- A Google Colab runtime
  - **local backend:** nothing extra — the server runs inside the Colab VM
  - **remote backend:** the bundled bridge running in Colab plus a tunnel
    (Cloudflare quick tunnel, `colab.output.serve_kernel_port_as_*`, etc.)

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
pip install -r colab_shell_mcp/requirements.txt
```

### Step 4 — Configure

```bash
cp colab_shell_mcp/.env.example colab_shell_mcp/.env
# Edit .env for the remote backend, or leave defaults for the local backend
```

---

## Backends

A hosted Colab runtime cannot be reached directly (no SSH, no Docker socket), so
the server has two backends selected by `COLAB_MODE`:

| Backend | When | How it reaches Colab |
|---------|------|----------------------|
| **local**  | The server runs **inside** the Colab VM (e.g. launched from a notebook cell). | Runs commands directly in-process. |
| **remote** | The server runs on **your laptop**, driving a remote Colab. | Talks HTTP to the bridge running in Colab, exposed through a tunnel. |

`COLAB_MODE=auto` (the default) picks **remote** when `COLAB_BRIDGE_URL` is set
and **local** otherwise.

---

## Running the Server

```bash
python colab_shell_mcp/server.py
```

- **Inside Colab (local backend):** the process already lives in the runtime, so
  no bridge is needed. Launch it and connect a chatbot running in the same VM.
- **On your laptop (remote backend):** set `COLAB_BRIDGE_URL` and
  `COLAB_BRIDGE_TOKEN` first (see below), then run the command above.

---

## Running the Bridge in Colab

The bridge is standard-library only, so it runs in a bare Colab kernel with no
`pip install` step. In a Colab cell:

```python
!git clone --depth 1 https://github.com/h1ddenpr0cess20/mcp.git
import subprocess, os, secrets
token = secrets.token_urlsafe(24)
env = {**os.environ, "COLAB_BRIDGE_TOKEN": token, "COLAB_BRIDGE_PORT": "8700"}
subprocess.Popen(["python", "-m", "colab_shell_client.bridge"],
                 cwd="mcp/colab_shell_mcp", env=env)
print("token:", token)
# Expose port 8700 with a tunnel (cloudflared quick tunnel, ngrok, etc.)
```

Then, on your laptop:

```bash
export COLAB_BRIDGE_URL="https://<your-tunnel>.trycloudflare.com"
export COLAB_BRIDGE_TOKEN="<token from the cell>"
python colab_shell_mcp/server.py
```

Every bridge endpoint except `/health` requires the bearer token, compared with
`hmac.compare_digest`.

---

## Environment Variables

| Variable                   | Default       | Description |
|----------------------------|---------------|-------------|
| `COLAB_MODE`               | `auto`        | `local`, `remote`, or `auto` (remote when a bridge URL is set) |
| `COLAB_BRIDGE_URL`         | *(none)*      | Bridge base URL for the remote backend |
| `COLAB_BRIDGE_TOKEN`       | *(none)*      | Bearer token the bridge printed |
| `COLAB_BRIDGE_VERIFY_TLS`  | `true`        | Verify the tunnel's TLS certificate |
| `CONNECT_TIMEOUT`          | `30`          | Connection/read timeout for bridge requests (seconds) |
| `COMMAND_TIMEOUT`          | `1200`        | Per-command execution timeout (seconds) |
| `COLAB_MCP_TRANSPORT`      | *(auto)*      | `http` or `stdio`; auto-detects from the tty |
| `COLAB_MCP_HOST`           | `127.0.0.1`   | MCP HTTP bind address |
| `COLAB_MCP_PORT`           | `9630`        | MCP HTTP port |

Bridge-side variables (set where the bridge runs, inside Colab):

| Variable              | Default       | Description |
|-----------------------|---------------|-------------|
| `COLAB_BRIDGE_HOST`   | `127.0.0.1`   | Bridge bind address |
| `COLAB_BRIDGE_PORT`   | `8700`        | Bridge port |
| `COLAB_BRIDGE_TOKEN`  | *(generated)* | Bearer token; printed if unset |
| `COMMAND_TIMEOUT`     | `1200`        | Per-command execution timeout (seconds) |

---

## File Server

`fetch_file` downloads files from the runtime and serves them over a local HTTP
server so the MCP client can retrieve them by URL.

| Variable           | Default       | Description |
|--------------------|---------------|-------------|
| `FILE_SERVER_HOST` | `127.0.0.1`   | Bind address |
| `FILE_SERVER_PORT` | `9631`        | Port |
| `FILES_DIR`        | `~/mcp-files` | Where fetched files are stored |

---

## Transport Options

The transport is chosen in the `__main__` block of `server.py` and can be
overridden with `COLAB_MCP_TRANSPORT`.

### HTTP (default when run in a terminal or Colab)

```python
mcp.run(transport="http", host="127.0.0.1", port=9630, path="/mcp")
```

Server listens at `http://127.0.0.1:9630/mcp`.

### stdio (default when spawned by an MCP client)

```python
mcp.run()
```

| Transport | When to use |
|-----------|-------------|
| stdio     | Clients that manage the server subprocess |
| HTTP      | Persistent server; multiple clients; running inside Colab |

---

## Connecting to an MCP Client

### Option A — stdio

1. Add an entry to your client's MCP server config:

    ```json
    {
      "mcpServers": {
        "colab-shell": {
          "command": "/absolute/path/to/mcp/.venv/bin/python",
          "args": ["/absolute/path/to/mcp/colab_shell_mcp/server.py"],
          "env": { "COLAB_MCP_TRANSPORT": "stdio" }
        }
      }
    }
    ```

2. Restart your MCP client.

### Option B — HTTP

1. Start the server (with `COLAB_MCP_TRANSPORT=http` if not running from a tty):

    ```bash
    python colab_shell_mcp/server.py
    ```

2. Point your client at:

    ```
    http://127.0.0.1:9630/mcp
    ```

To accept connections from other machines, set `COLAB_MCP_HOST=0.0.0.0`. Do not
expose the server to the public internet without additional authentication — it
grants unauthenticated command execution in the runtime.

---

## Note on browser reachability checks

Some chatbots (e.g. smoketest) check each MCP server's reachability *from the
browser* before advertising its tools. When the server runs inside a Colab VM,
the browser cannot see the VM's `127.0.0.1`, so a local URL is marked offline
and dropped. Expose the server through a tunnel and register the tunnel's HTTPS
URL instead — it is reachable both by the browser's check and by an in-VM
provider that calls the tools. The `smoketest` Colab notebook automates exactly
this.
