# Subagent MCP Server (FastMCP)

FastMCP server for delegating tasks to local LLM sub-agents via LM Studio or any OpenAI-compatible endpoint. Supports named agents with MCP server access for agentic tool use, multi-turn conversations, parallel execution across models and agents, and a configurable MCP server pool.

## Quickstart

```bash
# From the repo root (mcp/)
pip install -r subagent_mcp/requirements.txt
cp subagent_mcp/.env.example subagent_mcp/.env
# Edit .env with your endpoint settings
python subagent_mcp/server.py
```

The server runs on HTTP transport at `127.0.0.1:9810` by default.

## Tools

### Core
- **`ask_subagent`** — Send a prompt to a local LLM. Optionally specify a model, system prompt, temperature, and MCP servers for tool use.
- **`ask_subagent_with_context`** — Multi-turn chat with conversation history tracked by a conversation ID.
- **`ask_subagent_vision`** — Send an image and prompt to a vision-capable model.
- **`list_models`** — List all models loaded on the LLM endpoint.

### Parallel
- **`ask_multiple`** — Ask the same prompt to multiple models and compare answers.
- **`ask_agents_parallel`** — Send the same prompt to multiple named agents in parallel.
- **`benchmark_concurrency`** — Find the optimal worker count for parallel requests.

### Named Agents
- **`create_agent`** — Create a named agent with a system prompt, optional model, and MCP server access.
- **`ask_agent`** — Send a prompt to a named agent.
- **`list_agents`** — List all registered agents.
- **`delete_agent`** — Delete a named agent.

### MCP Server Pool
- **`add_mcp_server`** — Register an MCP server by name and URL so agents can use its tools.
- **`remove_mcp_server`** — Remove a server from the pool.
- **`list_mcp_servers`** — List registered MCP servers.
- **`refresh_mcp_server`** — Reconnect to a server and refresh its tool list.
- **`list_mcp_tools`** — List all tools available from pooled MCP servers.

## Configuration

Copy `.env.example` to `.env` and edit as needed.

| Variable | Default | Description |
|---|---|---|
| `SUBAGENT_BASE_URL` | `http://localhost:1234/v1` | OpenAI-compatible API base URL |
| `SUBAGENT_API_KEY` | `lm-studio` | API key for the endpoint |
| `SUBAGENT_DEFAULT_MODEL` | *(auto-detect)* | Default model; leave unset to use whatever is loaded |
| `SUBAGENT_MAX_TOKENS` | `4000` | Max response tokens |
| `SUBAGENT_TIMEOUT` | `600` | Request timeout in seconds |
| `SUBAGENT_TEMPERATURE` | `0.7` | Sampling temperature |
| `SUBAGENT_MAX_WORKERS` | *(auto-detect)* | Max parallel workers; leave unset to auto-calibrate |
| `SUBAGENT_MCP_SERVERS` | *(none)* | Comma-separated `name=url` pairs for MCP servers |

### MCP server pool

Pre-register MCP servers in `.env` so agents can use their tools:

```
SUBAGENT_MCP_SERVERS=web=http://127.0.0.1:9510/mcp,shell=http://127.0.0.1:9610/mcp
```

Servers can also be added at runtime via the `add_mcp_server` tool.

## How Tool Use Works

When `mcp_servers` is specified on `ask_subagent` or a named agent, the server:

1. Fetches tool schemas from the specified MCP servers
2. Includes them in the LLM request as function tools
3. When the LLM calls a tool, executes it against the target MCP server
4. Feeds the result back to the LLM
5. Repeats until the LLM produces a final text response (up to 10 turns)

## Code Structure

- `subagent_client/client.py`: `SubagentClient` — LLM communication via the Responses API.
- `subagent_client/mcp_pool.py`: `MCPPool` — MCP server pool management and tool execution.
- `subagent_client/agents.py`: `AgentRegistry` — Named agent storage.
- `subagent_client/conversation.py`: `ConversationManager` — Multi-turn conversation history.
- `server.py`: FastMCP tool definitions.

## Notes

- Uses the OpenAI Responses API (`/v1/responses`), not the chat completions endpoint.
- Tool schemas from MCP servers are automatically cleaned for LM Studio Jinja template compatibility.
- Parallel auto-calibration runs a short benchmark on first parallel call to find optimal concurrency.
- See `server.py` for transport options (HTTP, SSE, stdio).
