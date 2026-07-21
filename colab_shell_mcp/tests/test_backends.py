import base64
import json
from unittest.mock import MagicMock

import pytest

from colab_shell_client import LocalBackend, RemoteBridgeBackend, make_backend


def test_make_backend_defaults_to_local(monkeypatch):
    monkeypatch.delenv("COLAB_BRIDGE_URL", raising=False)
    monkeypatch.delenv("COLAB_MODE", raising=False)
    assert isinstance(make_backend(), LocalBackend)


def test_make_backend_uses_remote_when_url_set(monkeypatch):
    monkeypatch.setenv("COLAB_MODE", "auto")
    monkeypatch.setenv("COLAB_BRIDGE_URL", "https://example.trycloudflare.com")
    monkeypatch.setenv("COLAB_BRIDGE_TOKEN", "secret")
    assert isinstance(make_backend(), RemoteBridgeBackend)


def test_make_backend_local_ignores_bridge_url(monkeypatch):
    monkeypatch.setenv("COLAB_MODE", "local")
    monkeypatch.setenv("COLAB_BRIDGE_URL", "https://example.trycloudflare.com")
    assert isinstance(make_backend(), LocalBackend)


def _backend_with_client(monkeypatch):
    backend = RemoteBridgeBackend.__new__(RemoteBridgeBackend)
    backend.base_url = "https://colab.example"
    backend.command_timeout = 1200
    backend.connect_timeout = 30.0
    import httpx

    backend._httpx = httpx
    backend._client = MagicMock()
    return backend


def _response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_remote_read_bytes_decodes_base64(monkeypatch):
    backend = _backend_with_client(monkeypatch)
    encoded = base64.b64encode(b"hi there").decode()
    backend._client.post.return_value = _response({"content_b64": encoded, "size": 8})
    assert backend.read_bytes("/content/x") == {"data": b"hi there", "size": 8}


def test_remote_write_bytes_encodes_base64(monkeypatch):
    backend = _backend_with_client(monkeypatch)
    backend._client.post.return_value = _response({"path": "/content/x", "size": 3})
    backend.write_bytes("/content/x", b"abc")
    sent = backend._client.post.call_args.kwargs["json"]
    assert base64.b64decode(sent["content_b64"]) == b"abc"


def test_remote_run_extends_read_timeout(monkeypatch):
    backend = _backend_with_client(monkeypatch)
    backend._client.post.return_value = _response({"stdout": "", "stderr": "", "exit_code": 0})
    backend.run("sleep 1", timeout=100)
    assert backend._client.post.call_args.kwargs["timeout"] == 115


def test_remote_list_reads_entries(monkeypatch):
    backend = _backend_with_client(monkeypatch)
    backend._client.get.return_value = _response({"entries": [{"name": "a"}]})
    assert backend.list_dir("~") == [{"name": "a"}]


def test_remote_backend_requires_url():
    with pytest.raises(ValueError):
        RemoteBridgeBackend("", "token")
