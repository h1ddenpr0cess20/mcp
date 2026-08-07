import pytest
import httpx

from subagent_client import SubagentClient


class TestSubagentClient:
    @pytest.mark.unit
    def test_ask_basic(self, client, monkeypatch, mock_response):
        def mock_post(self_inner, url, **kwargs):
            resp = httpx.Response(200, json=mock_response)
            resp._request = httpx.Request("POST", url)
            return resp

        monkeypatch.setattr(httpx.Client, "post", mock_post)

        result = client.ask("Hello")
        assert result["content"] == "Test response from local LLM."
        assert result["reasoning"] == "I thought about it."
        assert result["model"] == "test-model"
        assert result["usage"]["total_tokens"] == 30

    @pytest.mark.unit
    def test_ask_with_instructions(self, client, monkeypatch, mock_response):
        captured = {}

        def mock_post(self_inner, url, **kwargs):
            captured["json"] = kwargs.get("json", {})
            resp = httpx.Response(200, json=mock_response)
            resp._request = httpx.Request("POST", url)
            return resp

        monkeypatch.setattr(httpx.Client, "post", mock_post)

        client.ask("Hello", system_prompt="Be helpful")
        body = captured["json"]
        assert body["input"] == "Hello"
        assert body["instructions"] == "Be helpful"

    @pytest.mark.unit
    def test_ask_with_context(self, client, monkeypatch, mock_response):
        captured = {}

        def mock_post(self_inner, url, **kwargs):
            captured["json"] = kwargs.get("json", {})
            resp = httpx.Response(200, json=mock_response)
            resp._request = httpx.Request("POST", url)
            return resp

        monkeypatch.setattr(httpx.Client, "post", mock_post)

        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        client.ask_with_context("Follow up", history, system_prompt="Be nice")
        body = captured["json"]
        input_items = body["input"]
        assert len(input_items) == 3
        assert input_items[0] == {"type": "message", "role": "user", "content": "Hi"}
        assert input_items[1] == {"type": "message", "role": "assistant", "content": "Hello!"}
        assert input_items[2] == {"type": "message", "role": "user", "content": "Follow up"}
        assert body["instructions"] == "Be nice"

    @pytest.mark.unit
    def test_ask_vision(self, client, monkeypatch, mock_response):
        captured = {}

        def mock_post(self_inner, url, **kwargs):
            captured["json"] = kwargs.get("json", {})
            resp = httpx.Response(200, json=mock_response)
            resp._request = httpx.Request("POST", url)
            return resp

        monkeypatch.setattr(httpx.Client, "post", mock_post)

        client.ask_vision("What is this?", "http://example.com/img.png")
        input_items = captured["json"]["input"]
        assert len(input_items) == 1
        content = input_items[0]["content"]
        assert content[0]["type"] == "input_image"
        assert content[1]["type"] == "input_text"

    @pytest.mark.unit
    def test_list_models(self, client, monkeypatch, mock_models_response):
        def mock_get(self_inner, url, **kwargs):
            resp = httpx.Response(200, json=mock_models_response)
            resp._request = httpx.Request("GET", url)
            return resp

        monkeypatch.setattr(httpx.Client, "get", mock_get)

        models = client.list_models()
        assert models == ["model-a", "model-b", "model-c"]

    @pytest.mark.unit
    def test_ask_custom_params(self, client, monkeypatch, mock_response):
        captured = {}

        def mock_post(self_inner, url, **kwargs):
            captured["json"] = kwargs.get("json", {})
            resp = httpx.Response(200, json=mock_response)
            resp._request = httpx.Request("POST", url)
            return resp

        monkeypatch.setattr(httpx.Client, "post", mock_post)

        client.ask("Hello", model="custom-model", max_tokens=500, temperature=0.2)
        body = captured["json"]
        assert body["model"] == "custom-model"
        assert body["max_output_tokens"] == 500
        assert body["temperature"] == 0.2

    @pytest.mark.unit
    def test_ask_uses_responses_endpoint(self, client, monkeypatch, mock_response):
        captured = {}

        def mock_post(self_inner, url, **kwargs):
            captured["url"] = url
            resp = httpx.Response(200, json=mock_response)
            resp._request = httpx.Request("POST", url)
            return resp

        monkeypatch.setattr(httpx.Client, "post", mock_post)

        client.ask("Hello")
        assert captured["url"] == "http://localhost:9999/v1/responses"

    @pytest.mark.unit
    def test_ask_http_error(self, client, monkeypatch):
        def mock_post(self_inner, url, **kwargs):
            resp = httpx.Response(500, text="Internal Server Error")
            resp._request = httpx.Request("POST", url)
            return resp

        monkeypatch.setattr(httpx.Client, "post", mock_post)

        with pytest.raises(httpx.HTTPStatusError):
            client.ask("Hello")

    @pytest.mark.unit
    def test_parse_response_no_reasoning(self, client):
        data = {
            "model": "test-model",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Just content."}],
                }
            ],
            "usage": {"input_tokens": 5, "output_tokens": 10, "total_tokens": 15},
        }
        result = SubagentClient._parse_response(data)
        assert result["content"] == "Just content."
        assert result["reasoning"] == ""
