import sys

from dotenv import load_dotenv
from fastmcp import FastMCP

from subagent_client import AgentRegistry, ConversationManager, MCPPool, SubagentClient

load_dotenv()

mcp = FastMCP("subagent")
_client = SubagentClient()
_agents = AgentRegistry()
_conversations = ConversationManager()
_mcp_pool = MCPPool()


@mcp.tool
def ask_subagent(prompt: str, model: str = "", system_prompt: str = "",
                 max_tokens: int = 0, temperature: float = -1.0,
                 mcp_servers: list[str] = []) -> dict:
    """Ask a local LLM sub-agent a question.

    Args:
        prompt: The question or task for the sub-agent.
        model: Model to use (empty for default).
        system_prompt: Optional system prompt to set the agent's behavior.
        max_tokens: Max response tokens (0 for default).
        temperature: Sampling temperature (-1 for default).
        mcp_servers: List of registered MCP server names the agent can use as tools.

    Returns:
        Dict with content, reasoning, model, and usage.
    """
    return _client.ask(
        prompt,
        model=model or None,
        system_prompt=system_prompt or None,
        max_tokens=max_tokens or None,
        temperature=temperature if temperature >= 0 else None,
        mcp_servers=mcp_servers or None,
        mcp_pool=_mcp_pool if mcp_servers else None,
    )


@mcp.tool
def ask_subagent_with_context(prompt: str, conversation_id: str,
                              model: str = "", system_prompt: str = "") -> dict:
    """Send a prompt with conversation history to a local LLM for multi-turn chat.

    Args:
        prompt: The follow-up question or task.
        conversation_id: ID to track the conversation across turns.
        model: Model to use (empty for default).
        system_prompt: Optional system prompt for the conversation.

    Returns:
        Dict with content, reasoning, model, and usage.
    """
    history = _conversations.get_history(conversation_id)
    result = _client.ask_with_context(
        prompt, history,
        model=model or None,
        system_prompt=system_prompt or None,
    )
    _conversations.add_exchange(conversation_id, prompt, result["content"])
    return result


@mcp.tool
def ask_subagent_vision(prompt: str, image_url: str, model: str = "") -> dict:
    """Ask a vision-capable local model about an image.

    Args:
        prompt: Question or task about the image.
        image_url: URL or base64 data URI of the image.
        model: Vision model to use (empty for default).

    Returns:
        Dict with content, model, and usage.
    """
    return _client.ask_vision(prompt, image_url, model=model or None)


@mcp.tool
def list_models() -> dict:
    """List available models on the local LLM endpoint.

    Returns:
        Dict with models (list of model IDs) and count.
    """
    models = _client.list_models()
    return {"models": models, "count": len(models)}


@mcp.tool
def ask_multiple(prompt: str, models: list[str] = []) -> dict:
    """Ask the same question to multiple local models and compare answers.

    Args:
        prompt: The question to ask each model.
        models: List of model IDs to query (empty for all available).

    Returns:
        Dict keyed by model ID with each model's response or error.
    """
    targets = models or _client.list_models()
    tasks = [{"prompt": prompt, "model": m, "label": m} for m in targets]
    return _client.ask_parallel(tasks)


# --- Agent management ---

@mcp.tool
def create_agent(name: str, system_prompt: str, model: str = "",
                 mcp_servers: list[str] = []) -> dict:
    """Create a named agent with a persistent system prompt, optional model, and MCP server access.

    Args:
        name: Unique name for the agent (e.g. "researcher", "devops").
        system_prompt: System prompt that defines the agent's behavior.
        model: Model to use for this agent (empty for default).
        mcp_servers: List of registered MCP server names this agent can use as tools.

    Returns:
        Dict with name and created status.
    """
    return _agents.create(name, system_prompt, model=model or None,
                          mcp_servers=mcp_servers or None)


@mcp.tool
def ask_agent(name: str, prompt: str) -> dict:
    """Send a prompt to a named agent that retains its system prompt and MCP tools.

    Args:
        name: Name of a previously created agent.
        prompt: The question or task for the agent.

    Returns:
        Dict with content, reasoning, model, and usage.
    """
    agent = _agents.get(name)
    if not agent:
        return {"error": f"Agent '{name}' not found. Available: {_agents.list()}"}
    servers = agent.get("mcp_servers") or []
    return _client.ask(
        prompt,
        model=agent.get("model"),
        system_prompt=agent["system_prompt"],
        mcp_servers=servers or None,
        mcp_pool=_mcp_pool if servers else None,
    )


@mcp.tool
def list_agents() -> dict:
    """List all registered agent names and their configs.

    Returns:
        Dict with agent names as keys and their configs as values.
    """
    return {name: _agents.get(name) for name in _agents.list()}


@mcp.tool
def ask_agents_parallel(prompt: str, agent_names: list[str], max_workers: int = 0) -> dict:
    """Send the same prompt to multiple named agents in parallel.

    Args:
        prompt: The question or task for each agent.
        agent_names: List of agent names to query.
        max_workers: Max concurrent requests (0 = auto-detected optimal).

    Returns:
        Dict keyed by agent name with each agent's response or error.
    """
    tasks = []
    for name in agent_names:
        agent = _agents.get(name)
        if not agent:
            continue
        tasks.append({
            "prompt": prompt,
            "model": agent.get("model"),
            "system_prompt": agent["system_prompt"],
            "label": name,
        })
    return _client.ask_parallel(tasks, max_workers=max_workers or None)


# --- MCP server pool management ---

@mcp.tool
def add_mcp_server(name: str, url: str) -> dict:
    """Register an MCP server so agents can use its tools.

    Args:
        name: Short name for the server (e.g. "web", "shell", "android").
        url: URL of the MCP server (e.g. "http://127.0.0.1:9610/mcp").

    Returns:
        Dict with name, url, and added status.
    """
    result = _mcp_pool.add_server(name, url)
    _mcp_pool.refresh_server(name)
    return result


@mcp.tool
def remove_mcp_server(name: str) -> dict:
    """Remove an MCP server from the pool.

    Args:
        name: Name of the server to remove.

    Returns:
        Dict with removed status.
    """
    return {"name": name, "removed": _mcp_pool.remove_server(name)}


@mcp.tool
def list_mcp_servers() -> dict:
    """List all registered MCP servers and their available tools.

    Returns:
        Dict with server names as keys and their info as values.
    """
    return _mcp_pool.list_servers()


@mcp.tool
def refresh_mcp_server(name: str) -> dict:
    """Reconnect to an MCP server and refresh its tool list.

    Args:
        name: Name of the server to refresh.

    Returns:
        Dict with server name and updated tool count.
    """
    tools = _mcp_pool.refresh_server(name)
    return {"name": name, "tools": len(tools)}


@mcp.tool
def list_mcp_tools(server_name: str = "") -> dict:
    """List all tools available from MCP servers in the pool.

    Args:
        server_name: Filter to a specific server (empty for all).

    Returns:
        Dict with tool definitions grouped by server.
    """
    servers = [server_name] if server_name else None
    tools = _mcp_pool.get_tools_for_servers(servers)
    return {"tools": tools, "count": len(tools)}


# --- Benchmark ---

@mcp.tool
def benchmark_concurrency(model: str = "", max_level: int = 4) -> dict:
    """Benchmark parallel concurrency to find the optimal worker count.

    Sends a short prompt at concurrency levels 1 through max_level and
    measures throughput. Returns per-level stats and a recommendation.

    Args:
        model: Model to benchmark (empty for default).
        max_level: Highest concurrency level to test (default 4).

    Returns:
        Dict with results per level and recommended worker count.
    """
    return _client.benchmark_concurrency(
        model=model or None,
        max_level=max_level,
    )


if __name__ == "__main__":
    if sys.stdin.isatty():
        mcp.run(transport="http", host="127.0.0.1", port=9810, path="/mcp")
    else:
        mcp.run()
