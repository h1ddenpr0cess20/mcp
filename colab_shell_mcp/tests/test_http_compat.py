import asyncio

from mcp_http_compat import StreamableHttpCompat


class _Recorder:
    """Minimal ASGI downstream app that records the scope it was called with."""

    def __init__(self):
        self.called = False
        self.scope = None

    async def __call__(self, scope, receive, send):
        self.called = True
        self.scope = scope
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"downstream"})


def _run(app, scope):
    sent = []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    asyncio.run(app(scope, receive, send))
    return sent


def _http_scope(method, path="/mcp", headers=None):
    return {"type": "http", "method": method, "path": path, "headers": headers or []}


def test_probe_get_is_short_circuited_to_200():
    downstream = _Recorder()
    app = StreamableHttpCompat(downstream, mcp_path="/mcp")
    sent = _run(app, _http_scope("GET", headers=[(b"accept", b"*/*")]))
    assert downstream.called is False  # never reached the transport
    assert sent[0]["status"] == 200
    assert sent[-1]["body"] == b'{"status":"ok"}'


def test_head_probe_returns_empty_body():
    downstream = _Recorder()
    app = StreamableHttpCompat(downstream)
    sent = _run(app, _http_scope("HEAD"))
    assert downstream.called is False
    assert sent[0]["status"] == 200
    assert sent[-1]["body"] == b""


def test_session_get_passes_through_to_transport():
    downstream = _Recorder()
    app = StreamableHttpCompat(downstream)
    scope = _http_scope("GET", headers=[(b"accept", b"text/event-stream"), (b"mcp-session-id", b"abc")])
    _run(app, scope)
    assert downstream.called is True


def test_lenient_post_accept_is_topped_up():
    downstream = _Recorder()
    app = StreamableHttpCompat(downstream)
    _run(app, _http_scope("POST", headers=[(b"accept", b"application/json")]))
    accept = dict(downstream.scope["headers"])[b"accept"]
    assert b"application/json" in accept
    assert b"text/event-stream" in accept


def test_post_without_accept_gets_both_types():
    downstream = _Recorder()
    app = StreamableHttpCompat(downstream)
    _run(app, _http_scope("POST", headers=[]))
    accept = dict(downstream.scope["headers"])[b"accept"]
    assert accept == b"application/json, text/event-stream"


def test_compliant_post_is_left_alone():
    downstream = _Recorder()
    app = StreamableHttpCompat(downstream)
    original = b"application/json, text/event-stream"
    _run(app, _http_scope("POST", headers=[(b"accept", original)]))
    assert dict(downstream.scope["headers"])[b"accept"] == original


def test_non_mcp_path_is_untouched():
    downstream = _Recorder()
    app = StreamableHttpCompat(downstream, mcp_path="/mcp")
    _run(app, _http_scope("GET", path="/other", headers=[(b"accept", b"*/*")]))
    assert downstream.called is True


def test_non_http_scope_passes_through():
    downstream = _Recorder()
    app = StreamableHttpCompat(downstream)
    asyncio.run(app({"type": "lifespan"}, None, lambda m: asyncio.sleep(0)))
    assert downstream.called is True
