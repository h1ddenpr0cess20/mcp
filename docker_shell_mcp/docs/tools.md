# Tool Reference

Complete reference for all tools exposed by the Docker Shell MCP server. The
"sandbox" is the auto-managed Docker container the server runs commands in.

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

Executes a Bash command in the container (`bash -lc`) and returns its output.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| command   | string | yes      | Bash command to execute. Supports pipes, redirects, and multi-statement commands. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| stdout    | string  | Standard output from the command |
| stderr    | string  | Standard error output |
| exit_code | integer | Exit status (0 = success; 124 = timed out) |

**Use cases**

- Run arbitrary commands, scripts, or programs in the container.
- Install packages with `apt` or `pip`, compile code, or run tests.
- Inspect logs, processes, or system state.

---

## list\_directory

Lists the contents of a directory in the container.

**Parameters**

| Parameter | Type   | Required | Default | Description |
|-----------|--------|----------|---------|-------------|
| path      | string | no       | `"~"`   | Directory path in the container. Supports `~` and `~/subdir` expansion. Defaults to the container home. |

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

Reads the contents of a file in the container and returns them as a string.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| path      | string | yes      | Path to the file in the container. |

**Returns**

The file contents as a plain string.

---

## write\_file

Writes content to a file in the container. Creates the file if it does not
exist; overwrites it if it does.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| path      | string | yes      | Destination path in the container. |
| content   | string | yes      | Content to write. |

**Returns**

| Field | Type    | Description |
|-------|---------|-------------|
| path  | string  | Resolved absolute path of the written file |
| size  | integer | Size of the written file in bytes |

---

## upload\_file

Copies a file from the MCP server host into the container (via `docker cp`).

**Parameters**

| Parameter   | Type   | Required | Description |
|-------------|--------|----------|-------------|
| local_path  | string | yes      | Path to the file on the MCP server host. |
| remote_path | string | yes      | Destination path in the container. |

**Returns**

| Field       | Type    | Description |
|-------------|---------|-------------|
| remote_path | string  | Resolved destination path in the container |
| size        | integer | Size of the uploaded file in bytes |

---

## download\_file

Copies a file from the container to the MCP server host (via `docker cp`).

**Parameters**

| Parameter   | Type   | Required | Description |
|-------------|--------|----------|-------------|
| remote_path | string | yes      | Path to the file in the container. |
| local_path  | string | yes      | Destination path on the MCP server host. |

**Returns**

| Field      | Type    | Description |
|------------|---------|-------------|
| local_path | string  | Destination path on the MCP server host |
| size       | integer | Size of the downloaded file in bytes |

---

## get\_system\_info

Returns basic system information from the container.

**Parameters**

None.

**Returns**

| Field          | Type   | Description |
|----------------|--------|-------------|
| hostname       | string | Container hostname |
| uptime         | string | Human-readable uptime, e.g. `"up 2 hours, 14 minutes"` |
| kernel         | string | Kernel version string |
| mem_total      | string | Total memory, e.g. `"2.0Gi"` |
| mem_used       | string | Used memory |
| mem_available  | string | Available memory |
| disk_total     | string | Total disk size on `/` |
| disk_used      | string | Used disk space |
| disk_available | string | Available disk space |
| disk_use_pct   | string | Disk usage percentage, e.g. `"42%"` |

On command failure, returns the raw stdout/stderr/exit_code dict instead.

---

## fetch\_file

Copies a file out of the container and makes it available via a local HTTP URL.
Useful for retrieving generated documents, archives, images, or any binary file
so the client can download it directly.

**Parameters**

| Parameter   | Type   | Required | Description |
|-------------|--------|----------|-------------|
| remote_path | string | yes      | Path to the file in the container. |

**Returns**

| Field     | Type    | Description |
|-----------|---------|-------------|
| file_id   | string  | Unique identifier for the file |
| url       | string  | Local HTTP URL where the file can be downloaded |
| filename  | string  | Filename extracted from the path |
| size      | integer | File size in bytes |
| mime_type | string  | MIME type inferred from the filename, e.g. `"application/pdf"` |

Files are saved to `~/mcp-files/` and served on `http://127.0.0.1:9621/` by
default. Downloads are namespaced by their source path so files with the same
basename do not clobber each other.

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
  "url": "http://127.0.0.1:9621/files/file_a1b2c3d4e5f67890/content",
  "filename": "report.pdf",
  "size": 204800,
  "mime_type": "application/pdf"
}
```

---

## Error Handling

All tools propagate exceptions directly to the MCP client as tool execution
errors rather than returning structured error dictionaries (except
`get_system_info`, which returns the raw command result on failure).

Common errors:

- `RuntimeError: The sandbox is still being prepared …` — the image is still
  building on first run. Retry the tool call once the build finishes.
- `RuntimeError: Docker command failed …` — the Docker CLI returned an error
  (e.g. daemon not running, missing permission for `sudo -n docker`).
- `FileNotFoundError` / `IOError` — a `docker cp` on a path that does not exist.
- A command that exceeds `COMMAND_TIMEOUT` (default 1200s) returns
  `exit_code: 124` from `execute_command` rather than raising.
