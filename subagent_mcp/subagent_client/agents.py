PRESET_AGENTS = {
    "reviewer": {
        "system_prompt": "You are a senior code reviewer. Be concise and focus on bugs and security issues.",
        "model": None,
    },
    "summarizer": {
        "system_prompt": "Summarize the given text in 3-5 bullet points.",
        "model": None,
    },
    "extractor": {
        "system_prompt": "Extract structured data from the text. Return valid JSON only.",
        "model": None,
    },
    "translator": {
        "system_prompt": "Translate the given text. Preserve formatting.",
        "model": None,
    },
}


class AgentRegistry:
    def __init__(self):
        self._agents = dict(PRESET_AGENTS)

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
