# Tool Reference

Complete reference for all tools exposed by the Colab Shell MCP server. The
"runtime" is the Google Colab VM the server is bound to — the same environment
as a `!command` notebook cell.

---

## Table of Contents

- [execute\_command](#execute_command)
- [list\_directory](#list_directory)
- [read\_file](#read_file)
- [write\_file](#write_file)
- [upload\_file](#upload_file)
- [download\_file](#download_file)
- [get\_system\_info](#get_system_info)
- [fetch\_file](#fetch_file)
- [Return Value Structure](#return-value-structure)
- [Error Handling](#error-handling)

---

## execute\_command

Executes a command in the Colab runtime's shell (`bash -lc`) and returns its output.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| command   | string | yes      | Shell command to execute. Supports pipes, redirects, and multi-statement commands. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output from the command |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success; 124 = timed out) |

**Use cases**

- Install packages with `pip` or `apt`, compile code, or run scripts.
- Train or run inference on the attached GPU/TPU.
- Inspect logs, processes, or system state in the runtime.

---

## list\_directory

Lists the contents of a directory in the Colab runtime.

**Parameters**

| Parameter | Type   | Required | Default | Description |
|-----------|--------|----------|---------|-------------|
| path      | string | no       | `"~"`   | Directory path in the runtime. Supports `~` and `~/subdir` expansion. Content usually lives under `/content`. |

**Returns**

A list of entry objects. Each object contains:

| Field       | Type    | Description |
|-------------|---------|-------------|
| name        | string  | File or directory name |
| size        | integer | Size in bytes |
| is_dir      | boolean | `true` if the entry is a directory |
| permissions | string  | Octal permission string, e.g. `"0o755"` |
| modified    | number  | Last-modified time as a Unix timestamp |

---

## read\_file

Reads the contents of a file in the Colab runtime and returns them as a string
(decoded as UTF-8, replacing undecodable bytes).

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| path      | string | yes      | Path to the file in the runtime, e.g. `/content/output.txt`. |

**Returns**

The file contents as a plain string.

---

## write\_file

Writes content to a file in the Colab runtime. Creates the file if it does not
exist; overwrites it if it does. Parent directories must already exist.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| path      | string | yes      | Destination path in the runtime. |
| content   | string | yes      | Content to write. |

**Returns**

| Field | Type    | Description |
|-------|---------|-------------|
| path  | string  | Resolved absolute path of the written file |
| size  | integer | Size of the written file in bytes |

---

## upload\_file

Uploads a file from the MCP server host into the Colab runtime. When the server
runs inside Colab (local backend), "host" and "runtime" are the same
filesystem; when it runs on your laptop (remote backend), the bytes are streamed
to the runtime over the bridge.

**Parameters**

| Parameter   | Type   | Required | Description |
|-------------|--------|----------|-------------|
| local_path  | string | yes      | Path to the file on the MCP server host. |
| remote_path | string | yes      | Destination path in the runtime, e.g. `/content/data.csv`. |

**Returns**

| Field       | Type    | Description |
|-------------|---------|-------------|
| remote_path | string  | Resolved destination path in the runtime |
| size        | integer | Size of the uploaded file in bytes |

---

## download\_file

Downloads a file from the Colab runtime to the MCP server host.

**Parameters**

| Parameter   | Type   | Required | Description |
|-------------|--------|----------|-------------|
| remote_path | string | yes      | Path to the file in the runtime. |
| local_path  | string | yes      | Destination path on the MCP server host. |

**Returns**

| Field      | Type    | Description |
|------------|---------|-------------|
| local_path | string  | Destination path on the MCP server host |
| size       | integer | Size of the downloaded file in bytes |

---

## get\_system\_info

Returns system information from the Colab runtime, including the attached
accelerator — Colab's headline feature.

**Parameters**

None.

**Returns**

| Field          | Type   | Description |
|----------------|--------|-------------|
| hostname       | string | Runtime hostname |
| kernel         | string | Kernel version string |
| python         | string | Python version in the runtime |
| uptime         | string | Human-readable uptime, e.g. `"2h 14m"` |
| gpu            | string | Attached GPU (name and memory) or `"none"` |
| mem_total      | string | Total memory, e.g. `"12.7Gi"` |
| mem_used       | string | Used memory |
| mem_available  | string | Available memory |
| disk_total     | string | Total disk size on `/` |
| disk_used      | string | Used disk space |
| disk_available | string | Available disk space |

---

## fetch\_file

Downloads a file from the Colab runtime and makes it available via a local HTTP
URL. Useful for retrieving generated documents, archives, images, or model
checkpoints so the client can download them directly.

**Parameters**

| Parameter   | Type   | Required | Description |
|-------------|--------|----------|-------------|
| remote_path | string | yes      | Path to the file in the runtime. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| file_id   | string  | Unique identifier for the file |
| url       | string  | Local HTTP URL where the file can be downloaded |
| filename  | string  | Filename extracted from the path |
| size      | integer | File size in bytes |
| mime_type | string  | MIME type inferred from the filename, e.g. `"application/pdf"` |

Files are saved to `~/mcp-files/` and served on `http://127.0.0.1:9631/` by default.

---

## Return Value Structure

### execute\_command

```json
{
  "stdout": "Hello, world!\n",
  "stderr": "",
  "exit_code": 0
}
```

### list\_directory entry

```json
{
  "name": "report.pdf",
  "size": 204800,
  "is_dir": false,
  "permissions": "0o644",
  "modified": 1710000000.0
}
```

### fetch\_file

```json
{
  "file_id": "file_a1b2c3d4e5f67890",
  "url": "http://127.0.0.1:9631/files/file_a1b2c3d4e5f67890/content",
  "filename": "report.pdf",
  "size": 204800,
  "mime_type": "application/pdf"
}
```

---

## Error Handling

All tools propagate exceptions directly to the MCP client as tool execution
errors rather than returning structured error dictionaries.

Common errors:

- `RuntimeError: Colab bridge request failed …` — the remote bridge is
  unreachable or the token is wrong. Confirm the bridge cell is still running in
  Colab and `COLAB_BRIDGE_URL` / `COLAB_BRIDGE_TOKEN` match what it printed.
- `FileNotFoundError` / `IOError` — a read, write, or list on a path that does
  not exist in the runtime.
- A command that exceeds `COMMAND_TIMEOUT` (default 1200s) returns
  `exit_code: 124` from `execute_command` rather than raising.
