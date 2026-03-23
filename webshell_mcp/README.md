# WebShell MCP Server (FastMCP)

FastMCP server combining sandboxed shell execution, file operations, web search, and URL fetching inside a single auto-provisioned VirtualBox VM. SearXNG runs as a systemd service on the VM, and all web fetching (curl_cffi, Playwright, trafilatura) executes inside the VM over SSH.

## Quickstart

```bash
# From the repo root (mcp/)
pip install -r webshell_mcp/requirements.txt
python webshell_mcp/server.py
```

The server runs on HTTP transport at `127.0.0.1:9710` by default. On first run with VirtualBox installed, the VM is created and provisioned automatically (10-20 minutes). Subsequent starts restore the `clean-base` snapshot and are ready in under two minutes.

> **No VirtualBox?** Set `SSH_HOST`, `SSH_USER`, and `SSH_KEY_PATH` in a `.env` file to point at any existing Linux host that has SearXNG, curl_cffi, trafilatura, and Playwright installed.

## Tools

- **`execute_command`** — Execute a shell command in the sandbox; returns stdout, stderr, and exit_code.
- **`list_directory`** — List files at a path in the sandbox with name, size, permissions, and modified timestamp.
- **`read_file`** — Read a file's contents from the sandbox.
- **`write_file`** — Write (create or overwrite) a file in the sandbox.
- **`upload_file`** — Upload a local file into the sandbox via SFTP.
- **`download_file`** — Download a file from the sandbox to the local machine via SFTP.
- **`get_system_info`** — Get hostname, uptime, kernel, memory, and disk usage from the sandbox.
- **`fetch_file`** — Download a file from the sandbox and serve it via a local HTTP URL (port 9712).
- **`web_search`** — Search the web via SearXNG across multiple engines with category and time filters.
- **`news_search`** — Search for recent news articles (convenience wrapper scoped to the news category).
- **`fetch_url`** — Fetch a URL and extract content as markdown, text, or HTML. Uses curl_cffi with Chrome TLS impersonation and Playwright fallback for JS-rendered pages — all executed inside the VM.

## Configuration

Copy `.env.example` to `.env` and fill in values.

### Connecting to an existing SSH host

| Variable | Default | Description |
|---|---|---|
| `SSH_HOST` | *(required)* | Host IP or hostname |
| `SSH_PORT` | `22` | SSH port |
| `SSH_USER` | *(required)* | SSH username |
| `SSH_KEY_PATH` | *(none)* | Path to private key (preferred) |
| `SSH_PASSWORD` | *(none)* | Password fallback if no key |
| `SSH_TIMEOUT` | `10` | Connection timeout (seconds) |
| `COMMAND_TIMEOUT` | `30` | Per-command timeout (seconds) |

### VirtualBox auto-managed VM (optional)

When `vboxmanage` is on PATH, `VMManager` automatically creates and installs a Debian VM as the sandbox with SearXNG, Playwright, curl_cffi, and trafilatura pre-installed. All variables below are optional.

| Variable | Default | Description |
|---|---|---|
| `VM_NAME` | `ai-webshell` | VirtualBox VM name |
| `VM_RAM` | `2048` | RAM in MB |
| `VM_CPUS` | `2` | vCPU count |
| `VM_DISK` | `30720` | Disk size in MB |
| `VM_PASS` | `changeme123` | Installer user password |
| `ISO_PATH` | `~/debian-13.4.0-amd64-netinst.iso` | Debian netinst ISO (downloaded if missing) |
| `NETWORK_MODE` | `nat` | `hostonly` \| `nat` \| `bridged` |
| `HOST_ONLY_IF` | `vboxnet0` | Host-only network interface |
| `SHARED_FOLDER` | `~/vm-share` | Shared folder path |
| `VM_SUDO` | `false` | Grant passwordless sudo to the sandbox user |
| `SEARXNG_PORT` | `8889` | SearXNG port inside the VM (also forwarded in NAT mode) |

### Web and search

| Variable | Default | Description |
|---|---|---|
| `SEARXNG_URL` | *(auto-detected)* | Override SearXNG URL (default: constructed from VM IP + port) |
| `SEARXNG_TIMEOUT` | `30` | SearXNG request timeout (seconds) |
| `FETCH_TIMEOUT` | `30` | URL fetch timeout (seconds) |
| `FETCH_PROXIES` | *(none)* | Comma-separated proxy URLs, rotated randomly per request |

### File server

`fetch_file` serves files from the sandbox via a local HTTP server.

| Variable | Default | Description |
|---|---|---|
| `FILE_SERVER_HOST` | `127.0.0.1` | Bind address |
| `FILE_SERVER_PORT` | `9712` | Port |

Files are stored in `~/mcp-files/`.

## Code Structure

- `webshell_client/client.py`: `ShellClient` — SSH/SFTP operations via paramiko.
- `webshell_client/vm_manager.py`: `VMManager` — VirtualBox VM lifecycle (create, install, start, wait for SSH). Installs SearXNG, Playwright, curl_cffi, and trafilatura on the VM.
- `webshell_client/search.py`: `SearchClient` — SearXNG search via httpx (runs on host, queries VM).
- `webshell_client/fetch.py`: `FetchClient` — Deploys a fetch script to the VM and executes it via SSH. All fetching runs inside the VM.
- `webshell_client/file_server.py`: `FileServer` — Local HTTP server for serving downloaded sandbox files.
- `server.py`: FastMCP tool definitions.

## Notes

- The VM is separate from `shell_mcp`'s `ai-sandbox` — both can run simultaneously without conflicts.
- SearXNG runs as a systemd service inside the VM and starts automatically on boot.
- URL fetching uses curl_cffi (Chrome TLS fingerprint) first, then falls back to a headless Chromium browser for JS-heavy pages. Both run inside the VM.
- With `nat` networking, SSH is port-forwarded to `127.0.0.1:2223` and SearXNG to `127.0.0.1:8889`.
- The VM unattended install takes 10-20 minutes on first run. A `clean-base` snapshot is taken automatically after install.
- See `server.py` for transport options (HTTP, SSE, stdio).
