# Tool Reference

Complete reference for all tools exposed by the Subagent MCP server.

---

## Table of Contents

- [ask\_subagent](#ask_subagent)
- [ask\_subagent\_with\_context](#ask_subagent_with_context)
- [ask\_subagent\_vision](#ask_subagent_vision)
- [list\_models](#list_models)
- [ask\_multiple](#ask_multiple)
- [create\_agent](#create_agent)
- [ask\_agent](#ask_agent)
- [list\_agents](#list_agents)
- [delete\_agent](#delete_agent)
- [ask\_agents\_parallel](#ask_agents_parallel)
- [add\_mcp\_server](#add_mcp_server)
- [remove\_mcp\_server](#remove_mcp_server)
- [list\_mcp\_servers](#list_mcp_servers)
- [refresh\_mcp\_server](#refresh_mcp_server)
- [list\_mcp\_tools](#list_mcp_tools)
- [benchmark\_concurrency](#benchmark_concurrency)
- [Error Handling](#error-handling)

---

## ask\_subagent

Send a prompt to a local LLM. Optionally equip the agent with tools from registered MCP servers for an agentic tool-use loop.

**Parameters**

| Parameter     | Type         | Required | Default   | Description |
|---------------|--------------|----------|-----------|-------------|
| prompt        | string       | yes      | —         | The question or task for the sub-agent. |
| model         | string       | no       | `""`      | Model to use (empty for default). |
| system_prompt | string       | no       | `""`      | System prompt to set the agent's behavior. |
| max_tokens    | integer      | no       | `0`       | Max response tokens (0 for default). |
| temperature   | float        | no       | `-1.0`    | Sampling temperature (-1 for default). |
| mcp_servers   | list[string] | no       | `[]`      | Registered MCP server names the agent can use as tools. |

**Returns**

| Field     | Type   | Description |
|-----------|--------|-------------|
| content   | string | The agent's text response |
| reasoning | string | Chain-of-thought reasoning (if the model produces it) |
| model     | string | Model ID used |
| usage     | object | Token usage statistics |

**Use cases**

- One-shot questions or tasks to a local LLM.
- Agentic workflows where the LLM can search the web, run shell commands, or use any other MCP server's tools.

---

## ask\_subagent\_with\_context

Send a prompt with conversation history for multi-turn chat. The server tracks history by conversation ID.

**Parameters**

| Parameter       | Type   | Required | Default | Description |
|-----------------|--------|----------|---------|-------------|
| prompt          | string | yes      | —       | The follow-up question or task. |
| conversation_id | string | yes      | —       | ID to track the conversation across turns. |
| model           | string | no       | `""`    | Model to use (empty for default). |
| system_prompt   | string | no       | `""`    | System prompt for the conversation. |

**Returns**

Same as `ask_subagent`.

**Use cases**

- Follow-up questions that require context from previous exchanges.
- Iterative refinement of an answer across multiple turns.

---

## ask\_subagent\_vision

Send an image and prompt to a vision-capable model.

**Parameters**

| Parameter | Type   | Required | Default | Description |
|-----------|--------|----------|---------|-------------|
| prompt    | string | yes      | —       | Question or task about the image. |
| image_url | string | yes      | —       | URL or base64 data URI of the image. |
| model     | string | no       | `""`    | Vision model to use (empty for default). |

**Returns**

Same as `ask_subagent`.

**Use cases**

- Describe or analyze an image.
- Extract text or data from a screenshot.
- Answer questions about visual content.

---

## list\_models

List all models currently loaded on the LLM endpoint.

**Parameters**

None.

**Returns**

| Field  | Type         | Description |
|--------|--------------|-------------|
| models | list[string] | List of model IDs |
| count  | integer      | Number of models |

---

## ask\_multiple

Ask the same question to multiple models and compare their answers. Runs in parallel.

**Parameters**

| Parameter | Type         | Required | Default | Description |
|-----------|--------------|----------|---------|-------------|
| prompt    | string       | yes      | —       | The question to ask each model. |
| models    | list[string] | no       | `[]`    | Model IDs to query (empty for all available). |

**Returns**

Dict keyed by model ID, each containing the model's response or an error.

---

## create\_agent

Create a named agent with a persistent system prompt. Agents can optionally be assigned a specific model and access to MCP servers.

**Parameters**

| Parameter     | Type         | Required | Default | Description |
|---------------|--------------|----------|---------|-------------|
| name          | string       | yes      | —       | Unique name for the agent. |
| system_prompt | string       | yes      | —       | System prompt that defines the agent's behavior. |
| model         | string       | no       | `""`    | Model for this agent (empty for default). |
| mcp_servers   | list[string] | no       | `[]`    | MCP server names this agent can use as tools. |

**Returns**

| Field   | Type    | Description |
|---------|---------|-------------|
| name    | string  | Agent name |
| created | boolean | `true` on success |

**Use cases**

- Create specialized agents: a researcher with web access, a devops agent with shell access, a code reviewer with a strict system prompt.
- Reuse the same agent configuration across multiple prompts without repeating the setup.

---

## ask\_agent

Send a prompt to a previously created named agent. The agent's system prompt and MCP server access are applied automatically.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| name      | string | yes      | Name of the agent. |
| prompt    | string | yes      | The question or task. |

**Returns**

Same as `ask_subagent`. Returns an error dict if the agent name is not found.

---

## list\_agents

List all registered agents and their configurations.

**Parameters**

None.

**Returns**

Dict with agent names as keys and their configs (system_prompt, model, mcp_servers) as values.

---

## delete\_agent

Delete a named agent.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| name      | string | yes      | Name of the agent to delete. |

**Returns**

| Field   | Type    | Description |
|---------|---------|-------------|
| name    | string  | Agent name |
| deleted | boolean | `true` if the agent existed and was deleted |

---

## ask\_agents\_parallel

Send the same prompt to multiple named agents in parallel and collect all responses.

**Parameters**

| Parameter   | Type         | Required | Default | Description |
|-------------|--------------|----------|---------|-------------|
| prompt      | string       | yes      | —       | The question or task for each agent. |
| agent_names | list[string] | yes      | —       | List of agent names to query. |
| max_workers | integer      | no       | `0`     | Max concurrent requests (0 = auto-detected). |

**Returns**

Dict keyed by agent name with each agent's response or error.

**Use cases**

- Get multiple perspectives on the same question from differently-configured agents.
- Fan out a task to specialist agents and compare results.

---

## add\_mcp\_server

Register an MCP server so agents can use its tools. The server's tool schemas are fetched immediately on registration.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| name      | string | yes      | Short name for the server (e.g. "web", "shell"). |
| url       | string | yes      | URL of the MCP server (e.g. "http://127.0.0.1:9610/mcp"). |

**Returns**

| Field | Type    | Description |
|-------|---------|-------------|
| name  | string  | Server name |
| url   | string  | Server URL |
| added | boolean | `true` on success |

---

## remove\_mcp\_server

Remove an MCP server from the pool.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| name      | string | yes      | Name of the server to remove. |

**Returns**

| Field   | Type    | Description |
|---------|---------|-------------|
| name    | string  | Server name |
| removed | boolean | `true` if the server existed and was removed |

---

## list\_mcp\_servers

List all registered MCP servers.

**Parameters**

None.

**Returns**

Dict with server names as keys and their URLs as values.

---

## refresh\_mcp\_server

Reconnect to an MCP server and refresh its tool list. Useful after the target server has been restarted or updated.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| name      | string | yes      | Name of the server to refresh. |

**Returns**

| Field | Type    | Description |
|-------|---------|-------------|
| name  | string  | Server name |
| tools | integer | Number of tools after refresh |

---

## list\_mcp\_tools

List all tools available from MCP servers in the pool.

**Parameters**

| Parameter   | Type   | Required | Default | Description |
|-------------|--------|----------|---------|-------------|
| server_name | string | no       | `""`    | Filter to a specific server (empty for all). |

**Returns**

List of tool definitions in OpenAI function format.

---

## benchmark\_concurrency

Benchmark parallel concurrency to find the optimal worker count for your hardware. Sends a short prompt at concurrency levels 1 through `max_level` and measures throughput.

**Parameters**

| Parameter | Type    | Required | Default | Description |
|-----------|---------|----------|---------|-------------|
| model     | string  | no       | `""`    | Model to benchmark (empty for default). |
| max_level | integer | no       | `4`     | Highest concurrency level to test. |

**Returns**

| Field           | Type         | Description |
|-----------------|--------------|-------------|
| results         | list[object] | Per-level stats (workers, wall_time, req_per_sec) |
| recommended     | integer      | Optimal worker count |
| benchmark_model | string       | Model used for the benchmark |

---

## Error Handling

Tools propagate exceptions to the MCP client as tool execution errors. Common errors:

- `httpx.HTTPStatusError` — LLM endpoint returned a non-2xx status (model not loaded, invalid request, etc).
- `httpx.ConnectError` — LLM endpoint is unreachable.
- `RuntimeError` — No models available on the endpoint.
- MCP pool errors (connection refused, timeout) when an agent tries to use tools from an MCP server that is not running.
