"""Keep the MCP Streamable-HTTP endpoint from 406-ing probes and lenient clients.

The MCP Streamable-HTTP spec requires every request to the `/mcp` endpoint to
`Accept` **both** `application/json` and `text/event-stream`; anything else gets
a `406 Not Acceptable`. In practice a lot of traffic does not send that exact
pair:

- Browser reachability probes / uptime monitors send `Accept: */*` (or nothing)
  and just want to know the host is alive.
- Some MCP client SDKs send only `application/json`.

Both show up as a stream of 406s in the server log (and the second case breaks
tool calls outright). This ASGI middleware sits in front of the transport and:

1. Answers probe-style `GET`/`HEAD` requests that carry no MCP session with a
   plain `200 {"status":"ok"}` — enough for a liveness check, and it never
   reaches (or disturbs) the transport.
2. Tops up the `Accept` header on everything else so the transport sees a
   spec-compliant request instead of rejecting it.

Real MCP traffic is untouched: `POST` JSON-RPC and session-bearing `GET` SSE
streams already satisfy (or get topped up to) the requirement and flow through
normally.
"""

from starlette.middleware import Middleware

_JSON = b"application/json"
_SSE = b"text/event-stream"


class StreamableHttpCompat:
    def __init__(self, app, mcp_path: str = "/mcp"):
        self.app = app
        self.mcp_path = mcp_path.rstrip("/") or "/"

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path", "").rstrip("/") != self.mcp_path:
            await self.app(scope, receive, send)
            return

        headers = scope["headers"]
        has_session = any(key == b"mcp-session-id" for key, _ in headers)
        method = scope.get("method", "GET")

        # A GET/HEAD with no session is a liveness probe, not an SSE stream
        # (real streams carry mcp-session-id). Answer it without touching the
        # transport, which would otherwise 406 it for lacking text/event-stream.
        if method in ("GET", "HEAD") and not has_session:
            body = b'{"status":"ok"}'
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", _JSON),
                    (b"content-length", str(len(body)).encode()),
                ],
            })
            await send({"type": "http.response.body", "body": b"" if method == "HEAD" else body})
            return

        # Otherwise top up Accept so the transport doesn't 406 a lenient client.
        accept = b""
        for key, value in headers:
            if key == b"accept":
                accept = value
                break
        missing = [media for media, present in ((_JSON, _JSON in accept), (_SSE, _SSE in accept)) if not present]
        if missing:
            extra = b", ".join(missing)
            merged = accept + b", " + extra if accept.strip() else extra
            scope = dict(scope)
            scope["headers"] = [(k, v) for k, v in headers if k != b"accept"] + [(b"accept", merged)]

        await self.app(scope, receive, send)


def serve_http(mcp, host: str, port: int, path: str = "/mcp") -> None:
    """Run a FastMCP server over Streamable HTTP with the compat middleware."""
    middleware = [Middleware(StreamableHttpCompat, mcp_path=path)]
    try:
        mcp.run(transport="http", host=host, port=port, path=path, middleware=middleware)
    except TypeError:
        # Older FastMCP whose run() doesn't forward middleware: build the app
        # and drive it with uvicorn directly.
        import uvicorn

        app = mcp.http_app(path=path, middleware=middleware)
        uvicorn.run(app, host=host, port=port)
