# Shell MCP Server (FastMCP)

FastMCP server for shell execution and file operations over SSH. Optionally auto-provisions a VirtualBox VM (Debian 13) as an isolated sandbox — if VirtualBox is not present, connects to any external SSH host.

## Quickstart

```bash
# From the repo root (mcp/)
pip install -r shell_mcp/requirements.txt
python shell_mcp/server.py
```

The server runs on HTTP transport at `127.0.0.1:9610` by default.

## Tools

- **`execute_command`** — Execute a shell command in the sandbox; returns stdout, stderr, and exit_code.
- **`list_directory`** — List files at a path in the sandbox with name, size, permissions, and modified timestamp.
- **`read_file`** — Read a file's contents from the sandbox.
- **`write_file`** — Write (create or overwrite) a file in the sandbox.
- **`upload_file`** — Upload a local file into the sandbox via SFTP.
- **`download_file`** — Download a file from the sandbox to the local machine via SFTP.
- **`get_system_info`** — Get hostname, uptime, kernel, memory, and disk usage from the sandbox.
- **`fetch_file`** — Download a file from the sandbox and serve it via a local HTTP URL (port 9611).

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

When `vboxmanage` is on PATH, `VMManager` automatically creates and installs a Debian VM as the sandbox. All variables below are optional.

The managed image includes a compact agent workstation: Git/Git LFS and SSH,
Python with common development and document libraries, Node.js/npm plus
TypeScript/ESLint/Prettier, C/C++ build tools, shell linting, modern search and
archive utilities, SQLite, Graphviz, image/media tools, and the LibreOffice,
Pandoc, PDF, OCR, spreadsheet, and presentation toolchain. Large secondary
language stacks and services are left project-local to keep the base VM lean.

| Variable | Default | Description |
|---|---|---|
| `VM_NAME` | `ai-sandbox` | VirtualBox VM name |
| `VM_RAM` | `2048` | RAM in MB |
| `VM_CPUS` | `2` | vCPU count |
| `VM_DISK` | `30720` | Disk size in MB |
| `VM_PASS` | `changeme123` | Installer user password |
| `ISO_PATH` | `~/debian-13.4.0-amd64-netinst.iso` | Debian netinst ISO (downloaded if missing) |
| `NETWORK_MODE` | `hostonly` | `hostonly` \| `nat` \| `bridged` |
| `HOST_ONLY_IF` | `vboxnet0` | Host-only network interface |
| `SHARED_FOLDER` | `~/vm-share` | Shared folder path |
| `VM_SUDO` | `false` | Grant passwordless sudo to the sandbox user |

### File server

`fetch_file` serves files from the sandbox via a local HTTP server.

| Variable | Default | Description |
|---|---|---|
| `FILE_SERVER_HOST` | `127.0.0.1` | Bind address |
| `FILE_SERVER_PORT` | `9611` | Port |

Files are stored in `~/mcp-files/`.

## Code Structure

- `shell_client/client.py`: `ShellClient` — SSH/SFTP operations via paramiko.
- `shell_client/file_server.py`: `FileServer` — Local HTTP server for serving downloaded sandbox files.
- `shell_client/vm_manager.py`: `VMManager` — VirtualBox VM lifecycle (create, install, start, wait for SSH).
- `server.py`: FastMCP tool definitions.

## Notes

- With `hostonly` networking, the sandbox gets two NICs: NAT (internet during install) and host-only (SSH access from host). The server connects via the host-only IP on port 22.
- The VM unattended install takes 10–20 minutes on first run. A versioned, validated toolchain snapshot is taken automatically after install.
- Existing legacy `clean-base` VMs are upgraded and re-snapshotted automatically on their next start.
- See `server.py` for transport options (HTTP, SSE, stdio).
