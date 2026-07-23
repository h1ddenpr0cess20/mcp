"""A tiny, dependency-free HTTP bridge that exposes Colab's shell.

Run this *inside* a Google Colab notebook when the MCP server lives somewhere
else (your laptop). It listens on localhost and every request runs against the
Colab runtime's own shell via :mod:`colab_shell_client.core`. Pair it with a
tunnel (Cloudflare quick tunnel, ``colab.output.serve_kernel_port_as_*``, etc.)
and point the MCP server's ``COLAB_BRIDGE_URL`` / ``COLAB_BRIDGE_TOKEN`` at it.

Standard library only: Colab kernels start bare and this must run with no
``pip install`` step. Launch it with ``python -m colab_shell_client.bridge``.

Endpoints (all except ``/health`` require ``Authorization: Bearer <token>``):

    GET  /health                        -> {"status": "ok", ...}
    POST /exec   {command, timeout?}    -> {stdout, stderr, exit_code}
    GET  /list   ?path=~                 -> {"entries": [...]}
    POST /read   {path}                 -> {content_b64, size}
    POST /write  {path, content_b64}    -> {path, size}
    GET  /system                        -> {hostname, uptime, gpu, ...}
"""

import base64
import hmac
import json
import os
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

try:  # Support both "python -m colab_shell_client.bridge" and a copied file.
    from . import core
except ImportError:  # pragma: no cover - standalone execution fallback
    import core  # type: ignore

VERSION = "0.1.0"
MAX_BODY_BYTES = 256 * 1024 * 1024
# A bridge endpoint is a remote-shell into the Colab VM. When it is reachable
# from anywhere but loopback (i.e. behind a tunnel), the bearer token is the
# only thing standing between the internet and arbitrary command execution, so
# reject anything a brute-force could realistically reach.
MIN_TOKEN_LENGTH = 16
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def _make_handler(token: str, command_timeout: int):
    class BridgeHandler(BaseHTTPRequestHandler):
        server_version = f"colab-shell-bridge/{VERSION}"

        def log_message(self, *_args, **_kwargs):
            pass

        # -- helpers -------------------------------------------------------
        def _send(self, status: int, payload: dict):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            header = self.headers.get("Authorization", "")
            prefix = "Bearer "
            if not header.startswith(prefix):
                return False
            return hmac.compare_digest(header[len(prefix):], token)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            if length > MAX_BODY_BYTES:
                raise ValueError("request body too large")
            return json.loads(self.rfile.read(length).decode("utf-8"))

        # -- routing -------------------------------------------------------
        def do_GET(self):
            route = urlparse(self.path)
            if route.path == "/health":
                self._send(200, {"status": "ok", "service": "colab-shell-bridge", "version": VERSION})
                return
            if not self._authorized():
                self._send(401, {"error": "unauthorized"})
                return
            try:
                if route.path == "/list":
                    params = parse_qs(route.query)
                    path = params.get("path", ["~"])[0]
                    self._send(200, {"entries": core.list_directory(path)})
                elif route.path == "/system":
                    self._send(200, core.system_info())
                else:
                    self._send(404, {"error": "not found"})
            except Exception as exc:  # noqa: BLE001 - report failures to the client
                self._send(500, {"error": str(exc)})

        def do_POST(self):
            if not self._authorized():
                self._send(401, {"error": "unauthorized"})
                return
            route = urlparse(self.path)
            try:
                body = self._read_json()
                if route.path == "/exec":
                    command = body.get("command", "")
                    timeout = int(body.get("timeout") or command_timeout)
                    self._send(200, core.run_command(command, timeout))
                elif route.path == "/read":
                    result = core.read_bytes(body["path"])
                    self._send(200, {
                        "content_b64": base64.b64encode(result["data"]).decode("ascii"),
                        "size": result["size"],
                    })
                elif route.path == "/write":
                    data = base64.b64decode(body.get("content_b64", ""))
                    self._send(200, core.write_bytes(body["path"], data))
                else:
                    self._send(404, {"error": "not found"})
            except Exception as exc:  # noqa: BLE001 - report failures to the client
                self._send(500, {"error": str(exc)})

    return BridgeHandler


def main() -> None:
    host = os.getenv("COLAB_BRIDGE_HOST", "127.0.0.1")
    port = int(os.getenv("COLAB_BRIDGE_PORT", "8700"))
    command_timeout = int(os.getenv("COMMAND_TIMEOUT", str(core.DEFAULT_COMMAND_TIMEOUT)))

    token = os.getenv("COLAB_BRIDGE_TOKEN", "").strip()
    if not token:
        token = secrets.token_urlsafe(24)
        # Printed so the notebook can capture it and hand it to the MCP server.
        # Anything that lands in shared notebook output leaks this token, so
        # keep saved copies of the notebook output-free (Edit > Clear all
        # outputs before sharing) and rotate the token if it may have leaked.
        print(f"COLAB_BRIDGE_TOKEN={token}", flush=True)
    elif len(token) < MIN_TOKEN_LENGTH:
        raise SystemExit(
            f"COLAB_BRIDGE_TOKEN is too short ({len(token)} chars); use at least "
            f"{MIN_TOKEN_LENGTH}. Generate a strong one with "
            "`python -c \"import secrets; print(secrets.token_urlsafe(24))\"` "
            "or leave it unset to auto-generate."
        )

    handler = _make_handler(token, command_timeout)
    server = ThreadingHTTPServer((host, port), handler)
    if host not in LOOPBACK_HOSTS:
        # Binding beyond loopback (or fronting loopback with a public tunnel)
        # exposes an authenticated remote shell. Make the blast radius explicit.
        print(
            f"WARNING: bridge bound to {host} — this is a remote shell into the "
            "Colab VM. Anyone with the URL and token can run arbitrary commands "
            "here. Do not mount Google Drive or run authenticate_user() in a "
            "runtime you expose this way.",
            flush=True,
        )
    print(f"colab-shell-bridge v{VERSION} listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())
