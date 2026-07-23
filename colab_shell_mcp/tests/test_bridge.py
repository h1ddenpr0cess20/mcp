import base64
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from colab_shell_client import bridge


@pytest.fixture()
def running_bridge():
    handler = bridge._make_handler(token="secret", command_timeout=30)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    base = f"http://{host}:{port}"
    try:
        yield base
    finally:
        server.shutdown()
        server.server_close()


def _request(base, path, *, method="GET", token="secret", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    if token is not None:
        req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode())


def test_health_needs_no_auth(running_bridge):
    status, body = _request(running_bridge, "/health", token=None)
    assert status == 200
    assert body["status"] == "ok"


def test_missing_token_is_rejected(running_bridge):
    with pytest.raises(urllib.error.HTTPError) as exc:
        _request(running_bridge, "/system", token=None)
    assert exc.value.code == 401


def test_wrong_token_is_rejected(running_bridge):
    with pytest.raises(urllib.error.HTTPError) as exc:
        _request(running_bridge, "/system", token="nope")
    assert exc.value.code == 401


def test_exec_runs_command(running_bridge):
    status, body = _request(
        running_bridge, "/exec", method="POST", payload={"command": "echo hi"}
    )
    assert status == 200
    assert body["stdout"].strip() == "hi"
    assert body["exit_code"] == 0


def test_main_rejects_short_token(monkeypatch):
    monkeypatch.setenv("COLAB_BRIDGE_TOKEN", "short")
    with pytest.raises(SystemExit) as exc:
        bridge.main()
    assert "too short" in str(exc.value)


def test_write_then_read_roundtrips(tmp_path, running_bridge):
    target = str(tmp_path / "file.bin")
    payload = {"path": target, "content_b64": base64.b64encode(b"data").decode()}
    status, body = _request(running_bridge, "/write", method="POST", payload=payload)
    assert status == 200 and body["size"] == 4

    status, body = _request(running_bridge, "/read", method="POST", payload={"path": target})
    assert status == 200
    assert base64.b64decode(body["content_b64"]) == b"data"
