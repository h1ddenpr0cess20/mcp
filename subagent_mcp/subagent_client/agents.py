PRESET_AGENTS = {
    "reviewer": {
        "system_prompt": (
            "You are a meticulous code reviewer. Identify bugs, security issues, "
            "and style problems, and suggest concrete improvements."
        ),
        "model": None,
        "mcp_servers": [],
    },
    "summarizer": {
        "system_prompt": (
            "You are a summarization assistant. Produce concise, accurate summaries "
            "that preserve the key points of the source material."
        ),
        "model": None,
        "mcp_servers": [],
    },
    "extractor": {
        "system_prompt": (
            "You extract structured information from unstructured text. Return only "
            "the requested fields, accurately and without commentary."
        ),
        "model": None,
        "mcp_servers": [],
    },
    "translator": {
        "system_prompt": (
            "You are a translation assistant. Translate text faithfully into the "
            "requested language, preserving tone and meaning."
        ),
        "model": None,
        "mcp_servers": [],
    },
}


class AgentRegistry:
    def __init__(self):
        self._agents = {
            name: dict(config) for name, config in PRESET_AGENTS.items()
        }

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
