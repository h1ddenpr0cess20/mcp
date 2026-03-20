class AgentRegistry:
    def __init__(self):
        self._agents = {}

    def create(self, name, system_prompt, model=None, mcp_servers=None):
        """Create or update a named agent with a system prompt, optional model, and MCP servers."""
        self._agents[name] = {
            "system_prompt": system_prompt,
            "model": model,
            "mcp_servers": mcp_servers or [],
        }
        return {"name": name, "created": True}

    def get(self, name):
        """Get an agent by name, or None if not found."""
        return self._agents.get(name)

    def list(self):
        """List all registered agent names."""
        return list(self._agents.keys())

    def delete(self, name):
        """Delete a named agent. Returns True if it existed."""
        return self._agents.pop(name, None) is not None
