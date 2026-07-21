# Colab Shell MCP Server

FastMCP server for shell execution and file operations inside a **Google Colab
runtime**. It exposes the same tool surface as `shell_mcp`, `docker_shell_mcp`,
and `webshell_mcp` — `execute_command`, `list_directory`, `read_file`,
`write_file`, `upload_file`, `download_file`, `get_system_info`, `fetch_file` —
so the shared `mcp-shell-coding-agent` workflow works against it unchanged. The
difference is where the shell lives: Colab's free CPU/GPU/TPU VM, the same
environment as a `!command` notebook cell.

Because a hosted Colab runtime can't be reached directly from your machine (no
SSH, no Docker socket), the server has two backends:

| Backend | When | How it reaches Colab |
|---|---|---|
| **local** | The server runs **inside** the Colab VM (e.g. launched from a notebook cell) | Runs commands directly in-process — it already *is* in Colab |
| **remote** | The server runs on **your laptop**, driving a remote Colab | Talks HTTP to the bundled `bridge` running in the Colab notebook, exposed through a tunnel |

`COLAB_MODE=auto` (the default) picks **remote** when `COLAB_BRIDGE_URL` is set
and **local** otherwise.

## Quickstart — inside Colab (local backend)

Run this in a Colab cell. The server executes Colab's own shell and serves MCP
over HTTP for a chatbot running in the same VM (e.g. smoketest with an
LM Studio / Ollama local provider):

```python
!git clone --depth 1 https://github.com/h1ddenpr0cess20/mcp.git
!pip install -q -r mcp/colab_shell_mcp/requirements.txt
import subprocess, os
env = {**os.environ, "COLAB_MODE": "local", "COLAB_MCP_TRANSPORT": "http"}
subprocess.Popen(["python", "mcp/colab_shell_mcp/server.py"], env=env)
# → MCP endpoint at http://127.0.0.1:9630/mcp
```

Then add `http://127.0.0.1:9630/mcp` as an MCP server in your chatbot's
settings. The `smoketest` Colab notebook includes a ready-made cell that does
exactly this.

## Quickstart — laptop → remote Colab (remote backend)

1. In a Colab cell, start the bridge and a tunnel:

   ```python
   !git clone --depth 1 https://github.com/h1ddenpr0cess20/mcp.git
   import subprocess, os, secrets
   token = secrets.token_urlsafe(24)
   env = {**os.environ, "COLAB_BRIDGE_TOKEN": token, "COLAB_BRIDGE_PORT": "8700"}
   subprocess.Popen(["python", "-m", "colab_shell_client.bridge"],
                    cwd="mcp/colab_shell_mcp", env=env)
   # Expose port 8700 with a tunnel (cloudflared quick tunnel, ngrok, etc.)
   print("token:", token)
   ```

2. On your laptop, point the server at the tunnel and run it:

   ```bash
   pip install -r colab_shell_mcp/requirements.txt
   export COLAB_BRIDGE_URL="https://<your-tunnel>.trycloudflare.com"
   export COLAB_BRIDGE_TOKEN="<token from the cell>"
   python colab_shell_mcp/server.py
   ```

Cloud providers (OpenAI/xAI) that dial the MCP server from their own
infrastructure need an `https://` URL; a local provider on your own machine can
use `http://127.0.0.1:9630/mcp`.

## Tools

- `execute_command` — run Bash commands and pipelines in Colab's shell
- `list_directory`, `read_file`, `write_file` — work with files in the runtime
- `upload_file`, `download_file` — copy files across the server↔Colab boundary
- `get_system_info` — hostname, uptime, kernel, memory, disk, and attached GPU
- `fetch_file` — expose a generated file at a local HTTP download URL

## Configuration

Copy `.env.example` to `.env`. Common settings:

| Variable | Default | Description |
|---|---|---|
| `COLAB_MODE` | `auto` | `local`, `remote`, or `auto` (remote when a bridge URL is set) |
| `COLAB_BRIDGE_URL` | *(none)* | Bridge base URL for the remote backend |
| `COLAB_BRIDGE_TOKEN` | *(none)* | Bearer token the bridge printed |
| `COLAB_BRIDGE_VERIFY_TLS` | `true` | Verify the tunnel's TLS certificate |
| `COMMAND_TIMEOUT` | `1200` | Per-command timeout in seconds |
| `COLAB_MCP_TRANSPORT` | *(auto)* | `http` or `stdio`; auto-detects from the tty |
| `COLAB_MCP_HOST` / `COLAB_MCP_PORT` | `127.0.0.1` / `9630` | MCP HTTP bind |
| `FILE_SERVER_HOST` / `FILE_SERVER_PORT` | `127.0.0.1` / `9631` | `fetch_file` server |

## Code Structure

- `colab_shell_client/core.py` — stdlib-only shell/file primitives (the shared
  source of truth for both backends and the bridge)
- `colab_shell_client/backends.py` — `LocalBackend`, `RemoteBridgeBackend`, and
  `make_backend`
- `colab_shell_client/client.py` — `ColabClient`, the common tool surface
- `colab_shell_client/bridge.py` — standalone stdlib HTTP bridge for Colab
  (`python -m colab_shell_client.bridge`)
- `colab_shell_client/file_server.py` — local HTTP server for `fetch_file`
- `server.py` — FastMCP tool definitions

## Documentation

- [`docs/configuration.md`](docs/configuration.md) — install, backends, bridge setup, env vars, transports, and connecting a client
- [`docs/tools.md`](docs/tools.md) — full reference for every tool, return shapes, and error handling
- [`docs/examples.md`](docs/examples.md) — worked workflows and sample prompts

## Notes

- The bridge is standard-library only on purpose: a fresh Colab kernel has no
  packages installed, and the bridge must run without a `pip install` step.
- Every bridge request except `/health` requires the bearer token; the token is
  compared with `hmac.compare_digest`.
- A Colab VM is ephemeral — it resets when the runtime is recycled. Archive
  anything worth keeping and hand it back with `fetch_file` or `download_file`.
- Colab's usage is governed by Google's terms; this is intended for interactive,
  user-driven coding sessions, not unattended or abusive workloads.
