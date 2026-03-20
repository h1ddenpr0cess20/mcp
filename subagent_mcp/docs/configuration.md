# Configuration

How to install, run, and connect the Subagent MCP server to an MCP client.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Server](#running-the-server)
- [LLM Endpoint](#llm-endpoint)
- [Model Selection](#model-selection)
- [Generation Settings](#generation-settings)
- [Parallelism](#parallelism)
- [MCP Server Pool](#mcp-server-pool)
- [Transport Options](#transport-options)
- [Connecting to an MCP Client](#connecting-to-an-mcp-client)
- [Connecting to Other MCP Clients](#connecting-to-other-mcp-clients)

---

## Requirements

- Python 3.10 or later
- A running OpenAI-compatible LLM endpoint (e.g. [LM Studio](https://lmstudio.ai/), [ollama](https://ollama.com/), [vLLM](https://github.com/vllm-project/vllm))
- The endpoint must support the Responses API (`/v1/responses`)

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
pip install -r subagent_mcp/requirements.txt
```

### Step 4 — Configure

```bash
cp subagent_mcp/.env.example subagent_mcp/.env
# Edit .env with your endpoint settings
```

---

## Running the Server

```bash
python subagent_mcp/server.py
```

---

## LLM Endpoint

The server connects to any OpenAI-compatible API that supports the Responses API.

| Variable           | Default                    | Description |
|--------------------|----------------------------|-------------|
| `SUBAGENT_BASE_URL` | `http://localhost:1234/v1` | API base URL |
| `SUBAGENT_API_KEY`  | `lm-studio`               | API key |

LM Studio's default endpoint works out of the box with no configuration changes.

---

## Model Selection

| Variable               | Default       | Description |
|------------------------|---------------|-------------|
| `SUBAGENT_DEFAULT_MODEL` | *(auto-detect)* | Default model ID |

When unset, the server queries the endpoint and uses the first loaded model. Models can also be specified per-request via the `model` parameter on any tool.

---

## Generation Settings

| Variable              | Default | Description |
|-----------------------|---------|-------------|
| `SUBAGENT_MAX_TOKENS`  | `4000`  | Max response tokens |
| `SUBAGENT_TIMEOUT`     | `600`   | Request timeout in seconds |
| `SUBAGENT_TEMPERATURE` | `0.7`   | Sampling temperature |

All three can be overridden per-request on `ask_subagent`.

---

## Parallelism

| Variable              | Default       | Description |
|-----------------------|---------------|-------------|
| `SUBAGENT_MAX_WORKERS` | *(auto-detect)* | Max concurrent parallel requests |

When unset, the server runs a concurrency benchmark on the first parallel call (`ask_multiple` or `ask_agents_parallel`) and caches the optimal worker count for the session.

Use `benchmark_concurrency` to manually test and find the best setting for your hardware.

---

## MCP Server Pool

Pre-register MCP servers so agents can use their tools in an agentic loop.

| Variable              | Default  | Description |
|-----------------------|----------|-------------|
| `SUBAGENT_MCP_SERVERS` | *(none)* | Comma-separated `name=url` pairs |

**Example:**

```
SUBAGENT_MCP_SERVERS=web=http://127.0.0.1:9510/mcp,shell=http://127.0.0.1:9610/mcp,android=http://127.0.0.1:9700/mcp
```

Servers configured here are registered at startup. Their tool schemas are fetched lazily on first use. Servers can also be added at runtime via the `add_mcp_server` tool.

The pooled MCP servers do not need to be running when the subagent server starts — they are connected on demand.

---

## Transport Options

The active transport is set in the `__main__` block of `server.py`.

### HTTP (default)

```python
mcp.run(transport="http", host="127.0.0.1", port=9810, path="/mcp")
```

Server listens at `http://127.0.0.1:9810/mcp`.

### stdio

```python
mcp.run()
```

### SSE

```python
mcp.run(transport="sse", host="127.0.0.1", port=9810)
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
        "subagent": {
          "command": "/absolute/path/to/mcp/.venv/bin/python",
          "args": ["/absolute/path/to/mcp/subagent_mcp/server.py"]
        }
      }
    }
    ```

3. Restart your MCP client.

### Option B — HTTP

1. Start the server:

    ```bash
    python subagent_mcp/server.py
    ```

2. Point your client at:

    ```
    http://127.0.0.1:9810/mcp
    ```

---

## Connecting to Other MCP Clients

Any MCP-compliant client can connect via HTTP:

```
http://127.0.0.1:9810/mcp
```

To use a different port, edit `server.py`:

```python
mcp.run(transport="http", host="127.0.0.1", port=9812, path="/mcp")
```

To accept connections from other machines:

```python
mcp.run(transport="http", host="0.0.0.0", port=9810, path="/mcp")
```

Do not expose the server to the public internet without additional authentication.
