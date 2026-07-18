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

On first start the server builds `shell-mcp-sandbox:latest` from Ubuntu 24.04,
creates the container, and mounts the named `shell-mcp-data` volume at
`/workspace`. Later starts reuse both. The build runs in the background with
progress streamed to stderr; tool calls made before the sandbox is ready return
an immediate "still being prepared" error instead of hanging — retry once the
build finishes. Direct launches use HTTP at
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
| `DOCKER_COMMAND` | `docker` | Docker command; works with rootless or group-enabled Docker |
| `DOCKER_IMAGE` | `shell-mcp-sandbox:latest` | Image to use; missing images are built from the bundled Dockerfile |
| `DOCKER_CONTAINER` | `shell-mcp-sandbox` | Managed container name |
| `DOCKER_VOLUME` | `shell-mcp-data` | Persistent volume mounted at the workdir |
| `DOCKER_NETWORK` | `bridge` | Docker network mode; use `none` to disable network access |
| `DOCKER_MEMORY` | `2g` | Container memory limit |
| `DOCKER_CPUS` | `2` | CPU limit |
| `DOCKER_PIDS_LIMIT` | `512` | Process limit |
| `DOCKER_USER` | `root` | User for container commands |
| `DOCKER_REMOVE_ON_EXIT` | `false` | Remove rather than stop the container on server exit |
| `COMMAND_TIMEOUT` | `1200` | Command timeout in seconds |

The default user is root inside the container so additional tools can be
installed with `apt`. Docker's isolation boundary is not equivalent to a
hardened VM; do not mount sensitive host paths or the Docker socket into this
sandbox. The server deliberately does neither.

The default command now invokes Docker without sudo. Historical note: the initial
AI-assisted implementation used `sudo -n docker` because Docker required sudo on
the development system at the time. Prefer rootless Docker; if your system still
requires sudo, explicitly set `DOCKER_COMMAND=sudo -n docker`. The `-n` flag
makes missing permission fail immediately instead of blocking an MCP process on
a password prompt.
