# Usage Examples

Practical workflows showing how to use the Docker Shell MCP server. Every tool
call runs inside the auto-managed Docker container.

---

## Table of Contents

- [Running Commands](#running-commands)
- [File Operations](#file-operations)
- [Transferring Files](#transferring-files)
- [System Monitoring](#system-monitoring)
- [Fetching Generated Files](#fetching-generated-files)
- [Sample Questions for an AI Assistant](#sample-questions-for-an-ai-assistant)

---

## Running Commands

**Goal:** Execute Bash commands in the container.

**Tool call:**

```
execute_command("uname -a")
```

**Multi-statement:**

```
execute_command("cd /workspace && git clone https://github.com/example/repo && cd repo && npm ci")
```

**Install a package:**

```
execute_command("apt-get update && apt-get install -y ffmpeg")
```

**Sample prompts to an AI assistant:**

> Run `df -h` in the container and tell me how much disk space is available.

> Install the `jq` package in the sandbox.

> Clone my repo into `/workspace` and run the test suite.

---

## File Operations

**Goal:** Read, write, and list files in the container without transferring them.

**List a directory:**

```
list_directory("/workspace")
```

**Read a file:**

```
read_file("/workspace/repo/package.json")
```

**Write a file:**

```
write_file("/workspace/run.sh", "#!/bin/bash\nnpm test\n")
```

**Sample prompts to an AI assistant:**

> List the files in `/workspace`.

> Read the `package.json` in my checked-out repo.

> Write a build script to `/workspace/build.sh`.

---

## Transferring Files

**Goal:** Move files between the MCP server host and the container.

**Upload a local file:**

```
upload_file("/home/user/data.csv", "/workspace/data.csv")
```

**Download a file from the container:**

```
download_file("/workspace/results.json", "/tmp/results.json")
```

**Sample prompts to an AI assistant:**

> Upload my local `/tmp/input.csv` into `/workspace`.

> Download the build output at `/workspace/dist/app.zip` to my machine.

---

## System Monitoring

**Goal:** Check the health and resource usage of the container.

**Tool call:**

```
get_system_info()
```

Returns hostname, uptime, kernel version, memory usage, and disk usage in one
call.

**Sample prompts to an AI assistant:**

> What is the current memory and disk usage in the sandbox?

> How long has the container been running?

---

## Fetching Generated Files

**Goal:** Retrieve a file generated in the container and get a URL to download it.

**Typical sequence:**

1. Generate the file:

    ```
    execute_command("cd /workspace && python3 generate_report.py")
    ```

2. Fetch it via HTTP:

    ```
    fetch_file("/workspace/report.pdf")
    ```

Returns a URL like `http://127.0.0.1:9621/files/<file_id>/content` that the
client can open directly.

**Sample prompts to an AI assistant:**

> Run my report generator and give me a link to download the output PDF.

> Zip up `/workspace/dist/` and fetch it so I can download it.

> Convert the CSV to an Excel file using Python and fetch the result.

---

## Sample Questions for an AI Assistant

**Development**
- Clone my project into `/workspace`, install dependencies, and run the tests.
- Build my Go project and tell me if there are any compile errors.
- Check the git log for the last 10 commits in `/workspace/repo`.

**File management**
- List all `.log` files in `/workspace` larger than 10MB.
- Read `/workspace/config.yaml` and summarise the configuration.

**Data processing**
- Run my Python ETL script and fetch the output CSV when it's done.
- Convert the video file to MP4 using ffmpeg and fetch it.
- Generate a PDF report from my data and give me a download link.
