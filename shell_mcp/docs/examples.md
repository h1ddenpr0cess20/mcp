# Usage Examples

Practical workflows showing how to use the Shell MCP server.

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

**Goal:** Execute shell commands in the sandbox.

**Tool call:**

```
execute_command("uname -a")
```

**Multi-statement:**

```
execute_command("cd /var/log && tail -n 50 syslog")
```

**Install a package:**

```
execute_command("apt-get install -y ffmpeg")
```

**Run a Python script:**

```
execute_command("python3 /home/ai-agent/script.py")
```

**Sample prompts to an AI assistant:**

> Run `df -h` in the sandbox and tell me how much disk space is available.

> Install the `jq` package in the sandbox.

> Check what processes are using the most CPU right now.

> Run my script at `/home/ai-agent/process_data.py` and show me the output.

---

## File Operations

**Goal:** Read, write, and list files in the sandbox without transferring them.

**List a directory:**

```
list_directory("~/projects")
```

**Read a config file:**

```
read_file("/etc/ssh/sshd_config")
```

**Write a file:**

```
write_file("~/scripts/hello.sh", "#!/bin/bash\necho Hello World\n")
```

**Sample prompts to an AI assistant:**

> List the files in my home directory in the sandbox.

> Read the contents of `/etc/hosts` in the sandbox.

> Write a cron job script to `/home/ai-agent/backup.sh`.

> Show me what's in the `/var/log` directory.

---

## Transferring Files

**Goal:** Move files between the local machine and the sandbox.

**Upload a local file:**

```
upload_file("/home/user/data.csv", "/home/ai-agent/data.csv")
```

**Download a file from the sandbox:**

```
download_file("/home/ai-agent/results.json", "/tmp/results.json")
```

**Sample prompts to an AI assistant:**

> Upload my local file `/tmp/input.csv` to the sandbox.

> Download the log file at `/var/log/app.log` to my local machine.

---

## System Monitoring

**Goal:** Check the health and resource usage of the sandbox.

**Tool call:**

```
get_system_info()
```

Returns hostname, uptime, kernel version, memory usage, and disk usage in one call.

**Sample prompts to an AI assistant:**

> What is the current memory and disk usage in the sandbox?

> How long has the sandbox been running?

> Give me a system health summary.

---

## Fetching Generated Files

**Goal:** Retrieve a file generated in the sandbox and get a URL to download it.

**Typical sequence:**

1. Run a command to generate the file:

    ```
    execute_command("cd /home/ai-agent && python3 generate_report.py")
    ```

2. Fetch it via HTTP:

    ```
    fetch_file("/home/ai-agent/report.pdf")
    ```

Returns a URL like `http://127.0.0.1:9611/files/<file_id>/content` that the client can open directly.

**Sample prompts to an AI assistant:**

> Run my report generator and give me a link to download the output PDF.

> Generate a zip archive of `/home/ai-agent/exports/` and fetch it so I can download it.

> Convert the CSV to an Excel file using Python and fetch the result.

---

## Sample Questions for an AI Assistant

**Development**
- Run the test suite at `/home/ai-agent/myproject` and show me any failures.
- Build my Go project and tell me if there are any compile errors.
- Check the git log in the sandbox for the last 10 commits.
- Set up a Python virtual environment and install requirements from `/home/ai-agent/app/requirements.txt`.

**File management**
- List all `.log` files in `/var/log` larger than 10MB.
- Read `/home/ai-agent/config.yaml` and summarise the configuration.
- Write a new crontab entry to run my backup script every night at 2am.

**System administration**
- Show me all running services and their status.
- What are the last 20 lines of `/var/log/syslog`?
- Check if port 8080 is open and what process is using it.
- Show disk usage broken down by directory under `/home`.

**Data processing**
- Run my Python ETL script and fetch the output CSV when it's done.
- Convert the video file to MP4 using ffmpeg and fetch it.
- Generate a PDF report from my data and give me a download link.
