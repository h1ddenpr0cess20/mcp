import pytest


MOCK_RESPONSE = {
    "id": "resp_test123",
    "object": "response",
    "status": "completed",
    "model": "test-model",
    "output": [
        {
            "id": "rs_reasoning",
            "type": "reasoning",
            "status": "completed",
            "content": [
                {"type": "reasoning_text", "text": "I thought about it."}
            ],
        },
        {
            "id": "msg_output",
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [
                {"type": "output_text", "text": "Test response from local LLM."}
            ],
        },
    ],
    "usage": {
        "input_tokens": 10,
        "output_tokens": 20,
        "total_tokens": 30,
    },
}

MOCK_MODELS_RESPONSE = {
    "data": [
        {"id": "model-a"},
        {"id": "model-b"},
        {"id": "model-c"},
    ]
}


@pytest.fixture
def mock_response():
    return MOCK_RESPONSE


@pytest.fixture
def mock_models_response():
    return MOCK_MODELS_RESPONSE


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SUBAGENT_BASE_URL", "http://localhost:9999/v1")
    monkeypatch.setenv("SUBAGENT_API_KEY", "test-key")
    monkeypatch.setenv("SUBAGENT_DEFAULT_MODEL", "test-model")
    monkeypatch.setenv("SUBAGENT_MAX_TOKENS", "100")
    monkeypatch.setenv("SUBAGENT_TIMEOUT", "5")
    monkeypatch.setenv("SUBAGENT_TEMPERATURE", "0.5")

    from subagent_client import SubagentClient
    return SubagentClient()
