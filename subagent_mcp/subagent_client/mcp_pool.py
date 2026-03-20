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
        self._load_from_env()

    def _load_from_env(self):
        """Load MCP servers from SUBAGENT_MCP_SERVERS env var.

        Format: name=url,name=url,...
        e.g. web=http://127.0.0.1:9510/mcp,shell=http://127.0.0.1:9610/mcp
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
            self.refresh_all()

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
            self._tool_map.pop(tool["function"]["name"], None)
        del self._servers[name]
        return True

    def list_servers(self):
        """List all registered servers and their tool counts."""
        return {
            name: {"url": s.url, "tools": len(s.tools)}
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
            func_tool = {
                "type": "function",
                "function": {
                    "name": f"{name}__{t.name}",
                    "description": t.description or "",
                    "parameters": params,
                },
            }
            tools.append(func_tool)
            self._tool_map[f"{name}__{t.name}"] = name

        server.tools = tools
        return tools

    def refresh_server(self, name):
        """Sync wrapper to refresh a server's tools."""
        return asyncio.run(self._refresh_server(name))

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
        names = server_names or list(self._servers.keys())
        tools = []
        for name in names:
            if name in self._servers:
                tools.extend(self._servers[name].tools)
        return tools

    def resolve_tool_call(self, tool_name):
        """Given a namespaced tool name, return (server_name, original_tool_name)."""
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
        return asyncio.run(self._call_tool(server_name, tool_name, arguments))
