import asyncio
import os
from dataclasses import dataclass, field

from fastmcp import Client


@dataclass
class MCPServer:
    name: str
    url: str
    tools: list[dict] = field(default_factory=list)


class MCPPool:
    """Manages connections to a pool of MCP servers and exposes their tools."""

    def __init__(self):
        self._servers: dict[str, MCPServer] = {}
        self._tool_map: dict[str, str] = {}  # tool_name -> server_name
        self._needs_refresh = False
        self._load_from_env()

    @staticmethod
    def _run_async(coro):
        """Run an async coroutine safely, whether or not an event loop exists."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
        else:
            return asyncio.run(coro)

    def _ensure_refreshed(self):
        """Lazy-refresh servers that were loaded from env but not yet connected."""
        if self._needs_refresh:
            self._needs_refresh = False
            self.refresh_all()

    def _load_from_env(self):
        """Load MCP servers from SUBAGENT_MCP_SERVERS env var.

        Format: name=url,name=url,...
        e.g. web=http://127.0.0.1:9510/mcp,shell=http://127.0.0.1:9610/mcp

        Servers are registered but NOT refreshed here — refresh is deferred
        to first use to avoid asyncio.run() conflicts with FastMCP's event loop.
        """
        raw = os.getenv("SUBAGENT_MCP_SERVERS", "")
        if not raw:
            return
        for entry in raw.split(","):
            entry = entry.strip()
            if "=" not in entry:
                continue
            name, url = entry.split("=", 1)
            self.add_server(name.strip(), url.strip())
        if self._servers:
            self._needs_refresh = True

    def add_server(self, name, url):
        """Register an MCP server by name and URL."""
        self._servers[name] = MCPServer(name=name, url=url)
        return {"name": name, "url": url, "added": True}

    def remove_server(self, name):
        """Remove an MCP server and its tools from the pool."""
        if name not in self._servers:
            return False
        old_tools = self._servers[name].tools
        for tool in old_tools:
            self._tool_map.pop(tool["name"], None)
        del self._servers[name]
        return True

    def list_servers(self):
        """List all registered servers."""
        return {
            name: {"url": s.url}
            for name, s in self._servers.items()
        }

    async def _refresh_server(self, name):
        """Connect to a server and fetch its tool schemas."""
        server = self._servers[name]
        client = Client(server.url)
        async with client:
            mcp_tools = await client.list_tools()

        tools = []
        for t in mcp_tools:
            params = t.inputSchema or {"type": "object", "properties": {}}
            params = self._clean_schema(params)
            func_tool = {
                "type": "function",
                "name": f"{name}__{t.name}",
                "description": t.description or "",
                "parameters": params,
            }
            tools.append(func_tool)
            self._tool_map[f"{name}__{t.name}"] = name

        server.tools = tools
        return tools

    @staticmethod
    def _clean_schema(schema):
        """Simplify JSON Schema for LLM compatibility.

        Removes anyOf/null patterns that break LM Studio's Jinja templates.
        """
        if not isinstance(schema, dict):
            return schema
        result = {}
        for key, value in schema.items():
            if key == "properties" and isinstance(value, dict):
                result[key] = {
                    k: MCPPool._clean_property(v) for k, v in value.items()
                }
            elif isinstance(value, dict):
                result[key] = MCPPool._clean_schema(value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _clean_property(prop):
        """Simplify a single property schema, resolving anyOf/null patterns."""
        if not isinstance(prop, dict):
            return prop
        # anyOf with null → extract the non-null type
        if "anyOf" in prop:
            non_null = [s for s in prop["anyOf"] if s.get("type") != "null"]
            if non_null:
                cleaned = dict(non_null[0])
                if "default" in prop and prop["default"] is not None:
                    cleaned["default"] = prop["default"]
                if "description" in prop:
                    cleaned["description"] = prop["description"]
                return cleaned
        return {k: MCPPool._clean_schema(v) if isinstance(v, dict) else v
                for k, v in prop.items()}

    def refresh_server(self, name):
        """Sync wrapper to refresh a server's tools."""
        return self._run_async(self._refresh_server(name))

    def refresh_all(self):
        """Refresh tools from all registered servers."""
        results = {}
        for name in self._servers:
            try:
                tools = self.refresh_server(name)
                results[name] = {"tools": len(tools)}
            except Exception as e:
                results[name] = {"error": str(e)}
        return results

    def get_tools_for_servers(self, server_names=None):
        """Get OpenAI-format tool definitions for the given servers (or all)."""
        self._ensure_refreshed()
        names = server_names or list(self._servers.keys())
        tools = []
        for name in names:
            if name in self._servers:
                tools.extend(self._servers[name].tools)
        return tools

    def resolve_tool_call(self, tool_name):
        """Given a namespaced tool name, return (server_name, original_tool_name)."""
        self._ensure_refreshed()
        server_name = self._tool_map.get(tool_name)
        if not server_name:
            return None, None
        original_name = tool_name[len(server_name) + 2:]  # strip "servername__"
        return server_name, original_name

    async def _call_tool(self, server_name, tool_name, arguments):
        """Execute a tool call against an MCP server."""
        server = self._servers[server_name]
        client = Client(server.url)
        async with client:
            result = await client.call_tool(tool_name, arguments)
        # Extract text content from the result
        parts = []
        for block in result.content:
            if hasattr(block, "text"):
                parts.append(block.text)
            elif hasattr(block, "data"):
                parts.append(f"[binary: {block.mimeType}]")
        return "\n".join(parts) if parts else str(result)

    def call_tool(self, server_name, tool_name, arguments):
        """Sync wrapper to call a tool on an MCP server."""
        return self._run_async(self._call_tool(server_name, tool_name, arguments))
