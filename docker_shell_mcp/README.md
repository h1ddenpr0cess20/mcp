# Docker Shell MCP Server

FastMCP server for shell execution and file operations inside an auto-managed
Docker container. It exposes the same tool surface as `shell_mcp` without
requiring SSH or VirtualBox.

## Quickstart

Requirements: Python 3.10+, the Docker CLI, and a running Docker daemon.

```bash
pip install -r docker_shell_mcp/requirements.txt
python docker_shell_mcp/server.py
```

On first start the server builds `shell-mcp-sandbox:latest` from Ubuntu 24.04
and creates the container, mounting the named `shell-mcp-data` volume at
`/workspace`. Later starts reuse the cached image, but by default each new
server start discards the previous container and workspace volume and creates
both fresh — the same clean-slate-per-session behavior as `shell_mcp` and
`webshell_mcp`, just implemented with a disposable container instead of a
restored VM snapshot. Set `DOCKER_EPHEMERAL=false` to keep the container and
workspace volume across restarts instead. The build runs in the background
with progress streamed to stderr; tool calls made before the sandbox is ready
return an immediate "still being prepared" error instead of hanging — retry
once the build finishes. Direct launches use HTTP at
`http://127.0.0.1:9620/mcp`; MCP client launches use stdio.

The image is designed as a batteries-included agent workspace. It includes
Git/GitHub tooling, C/C++ build tools, Python, Node/TypeScript, Go, Rust, Ruby,
Java, PHP and Lua; modern shell/search utilities; network diagnostics; SQL and
Redis clients; and common media, office, PDF, OCR, charting, data-science, web,
testing, and document-generation packages. Python packages live in an activated
virtual environment at `/opt/agent-venv`.

## Tools

- `execute_command` — run Bash commands and pipelines
- `list_directory`, `read_file`, `write_file` — work with container files
- `upload_file`, `download_file` — copy files across the container boundary
- `get_system_info` — inspect container system resources
- `fetch_file` — expose a generated file at a local HTTP download URL

## Configuration

Copy `.env.example` to `.env`. Useful settings include:

| Variable | Default | Description |
|---|---|---|
| `DOCKER_COMMAND` | auto-detected | Docker command to use. Left unset the server probes `docker` first and falls back to `sudo -n docker` only if the socket needs root. Set it to pin a command, e.g. `podman` |
| `DOCKER_IMAGE` | `shell-mcp-sandbox:latest` | Image to use; missing images are built from the bundled Dockerfile |
| `DOCKER_CONTAINER` | `shell-mcp-sandbox` | Managed container name |
| `DOCKER_VOLUME` | `shell-mcp-data` | Named volume mounted at the workdir |
| `DOCKER_NETWORK` | `bridge` | Docker network mode; use `none` to disable network access |
| `DOCKER_MEMORY` | `2g` | Container memory limit |
| `DOCKER_CPUS` | `2` | CPU limit |
| `DOCKER_PIDS_LIMIT` | `512` | Process limit |
| `DOCKER_USER` | `root` | User for container commands |
| `DOCKER_EPHEMERAL` | `true` | Discard the container and workspace volume from any previous session on server start, so every session begins from a clean sandbox. Set `false` to persist the workspace across restarts |
| `DOCKER_REMOVE_ON_EXIT` | `false` | Remove rather than stop the container on server exit |
| `COMMAND_TIMEOUT` | `1200` | Command timeout in seconds |

The default user is root inside the container so additional tools can be
installed with `apt`. Docker's isolation boundary is not equivalent to a
hardened VM; do not mount sensitive host paths or the Docker socket into this
sandbox. The server deliberately does neither.

## Docker access

No sudo is required when Docker is usable by the account running the server —
the common case with docker-group membership, rootless Docker, Docker Desktop,
or a remote `DOCKER_HOST`. On first use the server probes `docker`, and only
if that cannot reach the daemon does it try `sudo -n docker`. Setting
`DOCKER_COMMAND` skips the probe and uses that command as-is.

Docker commands are run with stdin closed, so a helper that tries to read from
the terminal (a sudo password prompt, most often) fails immediately with a
reported error instead of blocking the server on input it cannot supply. Any
sudo command should still include `-n`. If neither candidate reaches the
daemon, setup fails with what each one reported and how to fix it; the usual
remedy is:

```bash
sudo usermod -aG docker "$USER"   # then log out and back in
```
