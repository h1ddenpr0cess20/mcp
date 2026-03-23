# Usage Examples

Practical workflows showing how to use the WebShell MCP server. Each scenario includes sample questions you can ask an AI assistant connected to this server.

---

## Table of Contents

- [Running Commands](#running-commands)
- [File Operations](#file-operations)
- [Transferring Files](#transferring-files)
- [System Monitoring](#system-monitoring)
- [Fetching Generated Files](#fetching-generated-files)
- [Web Search](#web-search)
- [News Search](#news-search)
- [Fetching a URL](#fetching-a-url)
- [Search Then Fetch](#search-then-fetch)
- [Combined Shell and Web Workflows](#combined-shell-and-web-workflows)
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

Returns a URL like `http://127.0.0.1:9712/files/<file_id>/content` that the client can open directly.

**Sample prompts to an AI assistant:**

> Run my report generator and give me a link to download the output PDF.

> Generate a zip archive of `/home/ai-agent/exports/` and fetch it so I can download it.

> Convert the CSV to an Excel file using Python and fetch the result.

---

## Web Search

**Goal:** Find web pages on a topic.

**Tool call:**

```
web_search("python asyncio tutorial")
```

Returns up to 10 results with titles, URLs, and excerpts from multiple search engines.

**By site:**

```
web_search("site:github.com fastmcp examples")
```

**By time range:**

```
web_search("python 3.13 features", time_range="month")
```

**By category:**

```
web_search("large language models", categories="science", max_results=5)
```

**Sample prompts to an AI assistant:**

> Search the web for the best Python asyncio tutorials.

> Search GitHub for FastMCP example projects.

> Find recent blog posts about Rust from the last week.

---

## News Search

**Goal:** Get recent news on a topic.

**Tool call:**

```
news_search("artificial intelligence regulation")
```

Defaults to results from the past week. Adjust with `time_range`:

```
news_search("OpenAI", time_range="day")
```

**Sample prompts to an AI assistant:**

> What's in the news about AI regulation this week?

> Find the latest news about Anthropic.

> What happened with the US stock market today?

---

## Fetching a URL

**Goal:** Read the full content of a specific page.

**Tool call:**

```
fetch_url("https://docs.python.org/3/library/asyncio.html")
```

Returns the page title and extracted main content as Markdown, stripping navigation, ads, and boilerplate.

**Plain text output:**

```
fetch_url("https://example.com/article", output_format="text")
```

**Without links:**

```
fetch_url("https://example.com/article", include_links=False)
```

**Sample prompts to an AI assistant:**

> Fetch the Python asyncio documentation and summarise the key concepts.

> Read this article and give me the main points: https://example.com/article

> Get the content of the FastMCP README from GitHub.

---

## Search Then Fetch

**Goal:** Find a relevant page and then read its full content.

**Typical sequence:**

1. `web_search("MCP server python tutorial")` — find candidate pages
2. `fetch_url("https://...")` — read the most relevant result in full

**Sample prompts to an AI assistant:**

> Search for FastMCP documentation, then fetch and summarise the most relevant page.

> Find the Wikipedia article about the MCP protocol and read it.

> Search for Python packaging best practices and read the top result.

---

## Combined Shell and Web Workflows

**Goal:** Use both shell and web tools together in a single workflow.

**Research and implement:**

1. `web_search("python pdf generation reportlab")` — find how to do it
2. `fetch_url("https://...")` — read the documentation
3. `execute_command("pip3 install reportlab")` — install the library in the sandbox
4. `write_file("/home/ai-agent/gen_report.py", "...")` — write the script
5. `execute_command("python3 /home/ai-agent/gen_report.py")` — run it
6. `fetch_file("/home/ai-agent/output.pdf")` — get the result

**Download and process external data:**

1. `web_search("US census data CSV download")` — find the data source
2. `execute_command("curl -o /home/ai-agent/data.csv 'https://...'")` — download in the sandbox
3. `execute_command("python3 -c 'import pandas; ...'")` — process the data
4. `fetch_file("/home/ai-agent/results.xlsx")` — retrieve the output

**Sample prompts to an AI assistant:**

> Search for the latest Python release notes, read them, then write a summary script in the sandbox.

> Find a CSV dataset about world population, download it in the sandbox, and generate a chart.

> Look up how to use ffmpeg to convert video formats, then convert the file at `/home/ai-agent/input.avi` to MP4.

---

## Sample Questions for an AI Assistant

**Development**
- Run the test suite at `/home/ai-agent/myproject` and show me any failures.
- Build my Go project and tell me if there are any compile errors.
- Set up a Python virtual environment and install requirements from `/home/ai-agent/app/requirements.txt`.

**File management**
- List all `.log` files in `/var/log` larger than 10MB.
- Read `/home/ai-agent/config.yaml` and summarise the configuration.
- Write a new crontab entry to run my backup script every night at 2am.

**System administration**
- Show me all running services and their status.
- What are the last 20 lines of `/var/log/syslog`?
- Check if port 8080 is open and what process is using it.

**Research**
- Search the web for recent developments in quantum computing.
- What does the latest Python release include? Search for it and read the release notes.
- Find and summarise the top Stack Overflow answers about Python type hints.

**Current events**
- What's the top tech news today?
- Search for news about space exploration from the past week.

**Technical lookup**
- Find the official documentation for the `httpx` library and summarise the async API.
- Search GitHub for open source MCP server implementations.

**Data processing**
- Run my Python ETL script and fetch the output CSV when it's done.
- Search for a public dataset, download it in the sandbox, process it, and fetch the results.
- Generate a PDF report from my data and give me a download link.
