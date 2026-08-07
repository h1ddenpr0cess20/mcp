import pytest

from subagent_client import AgentRegistry


class TestAgentRegistry:
    @pytest.mark.unit
    def test_registry_starts_empty(self):
        registry = AgentRegistry()
        assert registry.list() == []

    @pytest.mark.unit
    def test_create_agent(self):
        registry = AgentRegistry()
        result = registry.create("coder", "You write Python code.", model="codellama")
        assert result == {"name": "coder", "created": True}
        agent = registry.get("coder")
        assert agent["system_prompt"] == "You write Python code."
        assert agent["model"] == "codellama"

    @pytest.mark.unit
    def test_get_nonexistent(self):
        registry = AgentRegistry()
        assert registry.get("nonexistent") is None

    @pytest.mark.unit
    def test_delete_agent(self):
        registry = AgentRegistry()
        registry.create("temp", "Temporary agent.")
        deleted = registry.delete("temp")
        assert deleted is True
        assert registry.get("temp") is None

    @pytest.mark.unit
    def test_delete_nonexistent(self):
        registry = AgentRegistry()
        deleted = registry.delete("nonexistent")
        assert deleted is False

    @pytest.mark.unit
    def test_overwrite_agent(self):
        registry = AgentRegistry()
        registry.create("reviewer", "New system prompt.", model="new-model")
        agent = registry.get("reviewer")
        assert agent["system_prompt"] == "New system prompt."
        assert agent["model"] == "new-model"


class TestConversationManager:
    @pytest.mark.unit
    def test_empty_history(self):
        from subagent_client import ConversationManager
        mgr = ConversationManager()
        assert mgr.get_history("unknown") == []

    @pytest.mark.unit
    def test_add_and_get(self):
        from subagent_client import ConversationManager
        mgr = ConversationManager()
        mgr.add_exchange("conv1", "Hi", "Hello!")
        history = mgr.get_history("conv1")
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hi"}
        assert history[1] == {"role": "assistant", "content": "Hello!"}

    @pytest.mark.unit
    def test_multiple_exchanges(self):
        from subagent_client import ConversationManager
        mgr = ConversationManager()
        mgr.add_exchange("conv1", "Hi", "Hello!")
        mgr.add_exchange("conv1", "How are you?", "Good!")
        history = mgr.get_history("conv1")
        assert len(history) == 4

    @pytest.mark.unit
    def test_list_conversations(self):
        from subagent_client import ConversationManager
        mgr = ConversationManager()
        mgr.add_exchange("conv1", "Hi", "Hello!")
        mgr.add_exchange("conv2", "Hey", "Hi!")
        convos = mgr.list_conversations()
        assert convos == {"conv1": 2, "conv2": 2}

    @pytest.mark.unit
    def test_delete_conversation(self):
        from subagent_client import ConversationManager
        mgr = ConversationManager()
        mgr.add_exchange("conv1", "Hi", "Hello!")
        deleted = mgr.delete("conv1")
        assert deleted is True
        assert mgr.get_history("conv1") == []
        deleted_again = mgr.delete("conv1")
        assert deleted_again is False
