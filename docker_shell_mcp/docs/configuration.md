# Configuration

How to install, run, and connect the Docker Shell MCP server to an MCP client.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Server](#running-the-server)
- [Container Settings](#container-settings)
- [Ephemeral vs. Persistent](#ephemeral-vs-persistent)
- [File Server](#file-server)
- [Transport Options](#transport-options)
- [Connecting to an MCP Client](#connecting-to-an-mcp-client)
- [Security Notes](#security-notes)

---

## Requirements

- Python 3.10 or later
- The Docker CLI and a running Docker daemon

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
pip install -r docker_shell_mcp/requirements.txt
```

### Step 4 — Configure

```bash
cp docker_shell_mcp/.env.example docker_shell_mcp/.env
# Edit .env if the defaults don't suit your Docker setup
```

---

## Running the Server

```bash
python docker_shell_mcp/server.py
```

On first start the server builds `shell-mcp-sandbox:latest` from Ubuntu 24.04
and creates the container, mounting the named `shell-mcp-data` volume at
`/workspace`. The build runs in the background with progress streamed to stderr;
tool calls made before the sandbox is ready return an immediate "still being
prepared" error instead of hanging — retry once the build finishes. Later starts
reuse the cached image.

---

## Container Settings

Set these in `.env` to control how the container is created and run.

| Variable              | Default                      | Description |
|-----------------------|------------------------------|-------------|
| `DOCKER_COMMAND`      | `sudo -n docker`             | Non-interactive Docker command; set to `docker` for rootless or group-enabled Docker |
| `DOCKER_IMAGE`        | `shell-mcp-sandbox:latest`   | Image to use; missing or stale images are built from the bundled Dockerfile |
| `DOCKER_CONTAINER`    | `shell-mcp-sandbox`          | Managed container name |
| `DOCKER_HOSTNAME`     | `shell-sandbox`              | Container hostname |
| `DOCKER_WORKDIR`      | `/workspace`                 | Working directory and volume mount point |
| `DOCKER_USER`         | `root`                       | User for container commands |
| `DOCKER_NETWORK`      | `bridge`                     | Docker network mode; use `none` to disable network access |
| `DOCKER_MEMORY`       | `2g`                         | Container memory limit |
| `DOCKER_CPUS`         | `2`                          | CPU limit |
| `DOCKER_PIDS_LIMIT`   | `512`                        | Process limit |
| `DOCKER_VOLUME`       | `shell-mcp-data`             | Named volume mounted at the workdir |
| `COMMAND_TIMEOUT`     | `1200`                       | Per-command execution timeout in seconds |

The container is created with `--security-opt no-new-privileges=true`.

---

## Ephemeral vs. Persistent

| Variable                | Default | Description |
|-------------------------|---------|-------------|
| `DOCKER_EPHEMERAL`      | `true`  | Discard the container and workspace volume from any previous session on server start, so every session begins from a clean sandbox. Set `false` to persist the workspace across restarts. |
| `DOCKER_REMOVE_ON_EXIT` | `false` | Remove (rather than stop) the container when the server exits. |

The default clean-slate-per-session behavior mirrors `shell_mcp` and
`webshell_mcp`, just implemented with a disposable container instead of a
restored VM snapshot.

---

## File Server

`fetch_file` copies files out of the container and serves them over a local HTTP
server so the MCP client can retrieve them by URL.

| Variable           | Default       | Description |
|--------------------|---------------|-------------|
| `FILE_SERVER_HOST` | `127.0.0.1`   | Bind address |
| `FILE_SERVER_PORT` | `9621`        | Port |
| `FILES_DIR`        | `~/mcp-files` | Where fetched files are stored |

---

## Transport Options

The transport is chosen in the `__main__` block of `server.py`: HTTP when
launched from a terminal, stdio when spawned by an MCP client.

### HTTP (default from a terminal)

```python
mcp.run(transport="http", host="127.0.0.1", port=9620, path="/mcp")
```

Server listens at `http://127.0.0.1:9620/mcp`.

### stdio (default when spawned by a client)

```python
mcp.run()
```

| Transport | When to use |
|-----------|-------------|
| stdio     | Clients that manage the server subprocess |
| HTTP      | Persistent server; multiple clients; easiest to debug |

---

## Connecting to an MCP Client

### Option A — stdio

1. Add an entry to your client's MCP server config:

    ```json
    {
      "mcpServers": {
        "docker-shell": {
          "command": "/absolute/path/to/mcp/.venv/bin/python",
          "args": ["/absolute/path/to/mcp/docker_shell_mcp/server.py"]
        }
      }
    }
    ```

2. Restart your MCP client.

### Option B — HTTP

1. Start the server:

    ```bash
    python docker_shell_mcp/server.py
    ```

2. Point your client at:

    ```
    http://127.0.0.1:9620/mcp
    ```

---

## Security Notes

The default user is root inside the container so additional tools can be
installed with `apt`. Docker's isolation boundary is not equivalent to a
hardened VM; do not mount sensitive host paths or the Docker socket into this
sandbox — the server deliberately does neither. The default `DOCKER_COMMAND`
expects passwordless sudo for Docker; `-n` makes a missing permission fail
immediately instead of blocking on a password prompt.
