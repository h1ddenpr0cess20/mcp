# Configuration Reference

All configuration is done through environment variables. Copy `.env.example` to `.env` in the `webshell_mcp/` directory and edit as needed. Variables not present in `.env` fall back to the defaults shown below.

> **New to .env files?** A `.env` file is a plain text file where each line has the form `VARIABLE=value`. The server reads it automatically on startup using `python-dotenv`. You do not need to export variables to your shell.

---

## SSH connection

These variables control how the server connects to the VM (or any external SSH target).

| Variable | Default | Type | Description |
|---|---|---|---|
| `SSH_HOST` | *(none)* | string | Host IP or hostname to connect to. Required when not using VirtualBox auto-management. |
| `SSH_PORT` | `22` | int | SSH port. In NAT mode with VirtualBox, the VM forwards port 22 to `127.0.0.1:2223` automatically — you do not need to change this. |
| `SSH_USER` | `ai-agent` | string | SSH username on the remote host. |
| `SSH_KEY_PATH` | `~/.ssh/ai_vm_key` | path | Path to the SSH private key. Used by preference. |
| `SSH_PASSWORD` | *(none)* | string | Password fallback if no private key is available. Not recommended. |
| `SSH_TIMEOUT` | `10` | int | TCP connection timeout in seconds. |
| `COMMAND_TIMEOUT` | `30` | int | Per-command execution timeout in seconds. Long-running commands (compilation, large downloads) may need this increased. |

---

## VirtualBox VM

These variables are used only when `vboxmanage` is found on PATH. When VirtualBox is not present, they are silently ignored.

| Variable | Default | Type | Description |
|---|---|---|---|
| `VM_NAME` | `ai-webshell` | string | VirtualBox VM name. Distinct from `shell_mcp`'s `ai-sandbox` so both can coexist. |
| `VM_RAM` | `2048` | int | RAM in MB. Increase to 4096 or more if running memory-intensive workloads. |
| `VM_CPUS` | `2` | int | Number of virtual CPUs. |
| `VM_DISK` | `30720` | int | Disk size in MB (30 GB). Set before first run; cannot be changed after VM creation without manual intervention. |
| `VM_PASS` | `changeme123` | string | Password used during unattended Debian install. Not used for SSH after install (key auth is configured automatically). |
| `ISO_PATH` | `~/debian-13.4.0-amd64-netinst.iso` | path | Path to the Debian 13 netinst ISO. Downloaded automatically from `cdimage.debian.org` if not present (~754 MB). Downloads are resumable. |
| `NETWORK_MODE` | `nat` | string | Network topology (see Network Modes below): `hostonly`, `nat`, or `bridged`. |
| `HOST_ONLY_IF` | `vboxnet0` | string | Host-only network interface name. Used only when `NETWORK_MODE=hostonly`. Created automatically if it does not exist. |
| `SHARED_FOLDER` | `~/vm-share` | path | Host directory mounted inside the VM at `/mnt/share`. Created on the host if it does not exist. |
| `VM_SUDO` | `false` | bool | When `true`, the VM user is granted passwordless `sudo`. Useful for system-level operations from `execute_command`. Accepted values: `true`, `1`, `yes`. |
| `SEARXNG_PORT` | `8889` | int | SearXNG port inside the VM. In NAT mode this port is also forwarded from the host. In hostonly and bridged modes, the host connects to this port on the VM IP directly. |

**Network modes**

| Mode | Description |
|---|---|
| `nat` | Single NAT NIC with SSH port-forwarded to `127.0.0.1:2223` and SearXNG to `127.0.0.1:8889`. Default. |
| `hostonly` | Two NICs: NAT (internet during install) and host-only (SSH and SearXNG access). Isolates the sandbox from external networks. |
| `bridged` | Sandbox bridges onto the host's physical network interface. |

On first run with no existing VM, the server will:
1. Download the Debian netinst ISO (~754 MB) if not present.
2. Generate an SSH key pair at `~/.ssh/ai_vm_key`.
3. Create and configure the VM.
4. Run the unattended Debian installer (~10–20 minutes).
5. Install SearXNG, Playwright, curl_cffi, and trafilatura inside the VM.
6. Validate the web, development, and document toolchains.
7. Take a versioned toolchain snapshot when validation succeeds.

An existing legacy `clean-base` snapshot is upgraded automatically on the next
server start. Package indexes are refreshed with retries, required tools fail
provisioning loudly, and release-specific optional packages are isolated so one
unavailable package cannot cancel the rest of the install.

Subsequent starts skip all of the above and connect immediately.

---

## Web and search

| Variable | Default | Type | Description |
|---|---|---|---|
| `SEARXNG_URL` | *(auto-detected)* | URL | Override the SearXNG URL. When omitted, the server constructs the URL from the VM's IP and `SEARXNG_PORT` at startup. Set this when pointing at an external SearXNG instance. |
| `SEARXNG_TIMEOUT` | `30` | float | HTTP timeout in seconds for SearXNG requests. |
| `FETCH_TIMEOUT` | `30` | float | Timeout in seconds for each `fetch_url` call (the `curl_cffi` fast path). The SSH command timeout is set to three times this value to allow for the Playwright fallback. |
| `FETCH_PROXIES` | *(none)* | string | Comma-separated list of proxy URLs. Rotated randomly per request. Used by both the `curl_cffi` fast path and the Playwright fallback. |

### Proxy format

Supported proxy schemes: `http://`, `https://`, `socks5://`. Authentication is optional.

```
FETCH_PROXIES=http://host:port,socks5://user:pass@host:port
```

---

## File server

The `fetch_file` tool downloads a file from the VM and serves it via a local HTTP server running on the host.

| Variable | Default | Type | Description |
|---|---|---|---|
| `FILE_SERVER_HOST` | `127.0.0.1` | string | Bind address for the local file server. Change to `0.0.0.0` to expose to the local network. |
| `FILE_SERVER_PORT` | `9712` | int | Port for the local file server. |
| `FILES_DIR` | `~/mcp-files` | path | Local directory where files downloaded from the VM are stored. Created automatically. |

Files are served at:

```
http://<FILE_SERVER_HOST>:<FILE_SERVER_PORT>/files/<file_id>/content
```

---

## Port summary

| Port | Where it runs | Purpose |
|---|---|---|
| `9710` | Host | MCP server HTTP transport |
| `9712` | Host | File server (fetch_file downloads) |
| `8889` | VM (and host in NAT mode) | SearXNG |
| `2223` | Host (NAT mode only) | SSH forwarded from VM port 22 |
| `22` | VM | SSH (direct, hostonly/bridged modes) |

---

## Transport Options

The active transport is set in the `__main__` block of `server.py`.

### HTTP (default)

```python
mcp.run(transport="http", host="127.0.0.1", port=9710, path="/mcp")
```

Server listens at `http://127.0.0.1:9710/mcp`.

### stdio

```python
mcp.run()
```

### SSE

```python
mcp.run(transport="sse", host="127.0.0.1", port=9710)
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
        "webshell": {
          "command": "/absolute/path/to/mcp/.venv/bin/python",
          "args": ["/absolute/path/to/mcp/webshell_mcp/server.py"]
        }
      }
    }
    ```

3. Restart your MCP client.

### Option B — HTTP

1. Start the server:

    ```bash
    python webshell_mcp/server.py
    ```

2. Point your client at:

    ```
    http://127.0.0.1:9710/mcp
    ```

---

## Connecting to Other MCP Clients

Any MCP-compliant client can connect via HTTP:

```
http://127.0.0.1:9710/mcp
```

To use a different port, edit `server.py`:

```python
mcp.run(transport="http", host="127.0.0.1", port=9712, path="/mcp")
```

To accept connections from other machines:

```python
mcp.run(transport="http", host="0.0.0.0", port=9710, path="/mcp")
```

Do not expose the server to the public internet without additional authentication.
