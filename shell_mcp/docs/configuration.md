# Configuration

How to install, run, and connect the Shell MCP server to an MCP client.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Server](#running-the-server)
- [SSH Target](#ssh-target)
- [VirtualBox Auto-Managed VM](#virtualbox-auto-managed-vm)
- [File Server](#file-server)
- [Transport Options](#transport-options)
- [Connecting to an MCP Client](#connecting-to-an-mcp-client)
- [Connecting to Other MCP Clients](#connecting-to-other-mcp-clients)

---

## Requirements

- Python 3.10 or later
- An SSH-accessible target, **or** VirtualBox with `vboxmanage` on `PATH` (for auto-provisioning)

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
pip install -r shell_mcp/requirements.txt
```

### Step 4 — Configure

```bash
cp shell_mcp/.env.example shell_mcp/.env
# Edit .env with your SSH credentials
```

---

## Running the Server

```bash
python shell_mcp/server.py
```

---

## SSH Target

Set these in `.env` to connect to an existing SSH host.

| Variable         | Default   | Description |
|------------------|-----------|-------------|
| `SSH_HOST`       | *(required)* | Host IP or hostname |
| `SSH_PORT`       | `22`      | SSH port |
| `SSH_USER`       | *(required)* | SSH username |
| `SSH_KEY_PATH`   | *(none)*  | Path to private key (recommended) |
| `SSH_PASSWORD`   | *(none)*  | Password fallback if no key |
| `SSH_TIMEOUT`    | `10`      | Connection timeout in seconds |
| `COMMAND_TIMEOUT`| `30`      | Per-command execution timeout in seconds |

Key authentication is used when `SSH_KEY_PATH` is set; otherwise password authentication is used.

---

## VirtualBox Auto-Managed VM

When `vboxmanage` is on `PATH`, the server can automatically create and manage a Debian VM as the sandbox. All variables are optional and have defaults.

| Variable         | Default                             | Description |
|------------------|-------------------------------------|-------------|
| `VM_NAME`        | `ai-sandbox`                        | VirtualBox VM name |
| `VM_RAM`         | `2048`                              | RAM in MB |
| `VM_CPUS`        | `2`                                 | vCPU count |
| `VM_DISK`        | `30720`                             | Disk size in MB |
| `VM_PASS`        | `changeme123`                       | Installer account password |
| `ISO_PATH`       | `~/debian-13.4.0-amd64-netinst.iso` | Debian netinst ISO (downloaded automatically if missing) |
| `NETWORK_MODE`   | `hostonly`                          | `hostonly` \| `nat` \| `bridged` |
| `HOST_ONLY_IF`   | `vboxnet0`                          | Host-only network interface name |
| `SHARED_FOLDER`  | `~/vm-share`                        | Host path mounted as `/mnt/share` inside the sandbox |
| `VM_SUDO`        | `false`                             | Grant passwordless sudo to the sandbox user |

**Network modes**

| Mode       | Description |
|------------|-------------|
| `hostonly` | Sandbox has two NICs: NAT (internet during install) and host-only (SSH access). Recommended — isolates the sandbox from external networks. |
| `nat`      | Single NAT NIC with SSH port-forwarded to `127.0.0.1:2222`. |
| `bridged`  | Sandbox bridges onto the host's physical network interface. |

On first run with no existing VM, the server will:
1. Download the Debian netinst ISO (~754 MB) if not present.
2. Generate an SSH key pair at `~/.ssh/ai_vm_key`.
3. Create and configure the VM.
4. Run the unattended Debian installer (~10–20 minutes).
5. Validate Git, Node.js, Python, build, and document tooling.
6. Take a versioned toolchain snapshot when validation succeeds.

An existing legacy `clean-base` snapshot is upgraded automatically on the next
server start. Package indexes are refreshed with retries, required tools fail
provisioning loudly, and release-specific optional packages are isolated so one
unavailable package cannot cancel the rest of the install.

Subsequent starts skip all of the above and connect immediately.

---

## File Server

`fetch_file` downloads files from the sandbox and serves them over a local HTTP server so the MCP client can retrieve them by URL.

| Variable           | Default       | Description |
|--------------------|---------------|-------------|
| `FILE_SERVER_HOST` | `127.0.0.1`   | Bind address |
| `FILE_SERVER_PORT` | `9611`        | Port |

Files are stored in `~/mcp-files/`.

---

## Transport Options

The active transport is set in the `__main__` block of `server.py`.

### HTTP (default)

```python
mcp.run(transport="http", host="127.0.0.1", port=9610, path="/mcp")
```

Server listens at `http://127.0.0.1:9610/mcp`.

### stdio

```python
mcp.run()
```

### SSE

```python
mcp.run(transport="sse", host="127.0.0.1", port=9610)
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
        "shell": {
          "command": "/absolute/path/to/mcp/.venv/bin/python",
          "args": ["/absolute/path/to/mcp/shell_mcp/server.py"]
        }
      }
    }
    ```

3. Restart your MCP client.

### Option B — HTTP

1. Start the server:

    ```bash
    python shell_mcp/server.py
    ```

2. Point your client at:

    ```
    http://127.0.0.1:9610/mcp
    ```

---

## Connecting to Other MCP Clients

Any MCP-compliant client can connect via HTTP:

```
http://127.0.0.1:9610/mcp
```

To use a different port, edit `server.py`:

```python
mcp.run(transport="http", host="127.0.0.1", port=9612, path="/mcp")
```

To accept connections from other machines:

```python
mcp.run(transport="http", host="0.0.0.0", port=9610, path="/mcp")
```

Do not expose the server to the public internet without additional authentication.
