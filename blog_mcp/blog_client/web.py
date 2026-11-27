import base64
import hmac
import os
import secrets
import ssl
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

from . import pages
from .client import BlogClient, BlogError
from .render import render_markdown

_LOOPBACK = {"127.0.0.1", "localhost", "::1"}

_SECURITY_HEADERS = {
    # No scripts, no frames, no third-party requests except images a post links to.
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' https: data:; "
        "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
    "Cache-Control": "private, no-store",
}


class _QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        """Drop resets, aborted TLS handshakes, and port scans silently instead of printing tracebacks."""


class BlogServer:
    """Password-protected, read-only web viewer for the private blog.

    Runs in a daemon thread next to the MCP server. Every request needs HTTP
    Basic credentials, including requests for draft posts. Posts are managed
    through the MCP tools; nothing here writes to the blog.
    """

    PAGE_SIZE = 10
    AUTH_FAIL_DELAY = 0.5  # seconds to stall a rejected login, to slow guessing
    REQUEST_TIMEOUT = 15
    POLL_INTERVAL = 0.5  # how often the serve loop checks for shutdown; stop() waits at most this long

    def __init__(
        self,
        client: BlogClient,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        title: str | None = None,
        description: str | None = None,
        tls_cert: str | None = None,
        tls_key: str | None = None,
    ):
        self.client = client
        self.host = host if host is not None else os.getenv("BLOG_HOST", "127.0.0.1")
        self.port = port if port is not None else int(os.getenv("BLOG_PORT", "9411"))
        self.username = username if username is not None else os.getenv("BLOG_USERNAME", "owner")
        if not self.username or ":" in self.username:
            raise ValueError("BLOG_USERNAME must be non-empty and must not contain ':'")
        self.site = {
            "title": title if title is not None else os.getenv("BLOG_TITLE", "Private Blog"),
            "description": description if description is not None else os.getenv("BLOG_DESCRIPTION", ""),
        }
        self.tls_cert = os.path.expanduser(tls_cert if tls_cert is not None else os.getenv("BLOG_TLS_CERT", ""))
        self.tls_key = os.path.expanduser(tls_key if tls_key is not None else os.getenv("BLOG_TLS_KEY", ""))
        if bool(self.tls_cert) != bool(self.tls_key):
            raise ValueError("BLOG_TLS_CERT and BLOG_TLS_KEY must be set together")

        self.password_file: Path = client.data_dir / "viewer_password"
        configured = password if password is not None else os.getenv("BLOG_PASSWORD", "")
        if configured:
            self.password = configured
            self.password_source = "BLOG_PASSWORD"
        else:
            self.password = self._load_or_create_password()
            self.password_source = str(self.password_file)
        self._server: ThreadingHTTPServer | None = None

    # --- credentials -------------------------------------------------------

    def _load_or_create_password(self) -> str:
        try:
            existing = self.password_file.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            existing = ""
        if existing:
            return existing
        password = secrets.token_urlsafe(18)
        fd = os.open(self.password_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(password + "\n")
        os.chmod(self.password_file, 0o600)
        return password

    def authorized(self, header: str | None) -> bool:
        """Check an Authorization header against the configured credentials in constant time."""
        if not header or header[:6].lower() != "basic ":
            return False
        try:
            decoded = base64.b64decode(header[6:].strip(), validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return False
        user, sep, password = decoded.partition(":")
        if not sep:
            return False
        user_ok = hmac.compare_digest(user.encode(), self.username.encode())
        password_ok = hmac.compare_digest(password.encode(), self.password.encode())
        return user_ok and password_ok

    # --- addresses ---------------------------------------------------------

    @property
    def scheme(self) -> str:
        return "https" if self.tls_cert else "http"

    @property
    def base_url(self) -> str:
        host = "127.0.0.1" if self.host in ("0.0.0.0", "::", "") else self.host
        if ":" in host:
            host = f"[{host}]"
        return f"{self.scheme}://{host}:{self.port}"

    def post_url(self, slug: str) -> str:
        return f"{self.base_url}/post/{quote(slug, safe='')}"

    # --- routing -----------------------------------------------------------

    def dispatch(self, path: str, query: dict[str, list[str]]) -> tuple[int, str]:
        """Map a request path to (status, html). Authentication has already happened."""
        segments = [unquote(part) for part in path.split("/") if part]
        site = self.site
        if not segments:
            return 200, self._listing("Posts", "published", "", "/", query, "No posts have been published yet.")
        head, rest = segments[0], segments[1:]
        if head == "post" and len(rest) == 1:
            try:
                post = self.client.get_post(rest[0])
            except BlogError:
                return 404, pages.not_found_page(site, "There is no post with that address.")
            return 200, pages.post_page(site, post, render_markdown(post["body"]))
        if head == "tag" and len(rest) == 1:
            return 200, self._listing(f"Tagged #{rest[0]}", "published", rest[0], f"/tag/{quote(rest[0], safe='')}", query,
                                      "No published posts have this tag.")
        if head == "drafts" and not rest:
            return 200, self._listing("Drafts", "draft", "", "/drafts", query, "No drafts.")
        if head == "tags" and not rest:
            return 200, pages.tags_page(site, self.client.list_tags(status="published")["tags"])
        if head == "search" and not rest:
            text = (query.get("q") or [""])[0].strip()[:200]
            if not text:
                return 200, pages.search_page(site, "", None)
            return 200, pages.search_page(site, text, self.client.search_posts(text, limit=50)["posts"])
        return 404, pages.not_found_page(site)

    def _listing(self, heading: str, status: str, tag: str, base: str, query: dict[str, list[str]], empty: str) -> str:
        try:
            page = max(1, int((query.get("page") or ["1"])[0]))
        except ValueError:
            page = 1
        listing = self.client.list_posts(status=status, tag=tag, limit=self.PAGE_SIZE, offset=(page - 1) * self.PAGE_SIZE)
        return pages.post_list(self.site, heading, listing, base, page, self.PAGE_SIZE, empty)

    # --- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        """Start serving in a daemon thread. Raises OSError if the port is taken."""
        viewer = self

        class _Handler(BaseHTTPRequestHandler):
            timeout = viewer.REQUEST_TIMEOUT

            def _respond(self, status: int, body: str, headers: dict | None = None, send_body: bool = True) -> None:
                data = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Length", str(len(data)))
                merged = {"Content-Type": "text/html; charset=utf-8", **_SECURITY_HEADERS, **(headers or {})}
                for name, value in merged.items():
                    self.send_header(name, value)
                self.end_headers()
                if send_body:
                    self.wfile.write(data)

            def _handle(self, send_body: bool) -> None:
                if not viewer.authorized(self.headers.get("Authorization")):
                    time.sleep(viewer.AUTH_FAIL_DELAY)
                    self._respond(401, "Authentication required.\n",
                                  {"WWW-Authenticate": 'Basic realm="Private blog", charset="UTF-8"',
                                   "Content-Type": "text/plain; charset=utf-8"}, send_body)
                    return
                parts = urlsplit(self.path)
                try:
                    status, body = viewer.dispatch(parts.path, parse_qs(parts.query))
                except Exception as exc:  # never leak internals to the browser
                    sys.stderr.write(f"[blog] viewer error on {parts.path}: {exc!r}\n")
                    status, body = 500, pages.message_page(viewer.site, "Error", "Something went wrong.")
                self._respond(status, body, send_body=send_body)

            def do_GET(self):
                self._handle(send_body=True)

            def do_HEAD(self):
                self._handle(send_body=False)

            def log_message(self, *args, **kwargs):
                pass

        server = _QuietServer((self.host, self.port), _Handler)
        if self.tls_cert:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(self.tls_cert, self.tls_key)
            # Handshake lazily, in the per-request thread, so one stalled client cannot block accept().
            server.socket = context.wrap_socket(server.socket, server_side=True, do_handshake_on_connect=False)
        elif self.host not in _LOOPBACK:
            sys.stderr.write(
                f"[blog] WARNING: viewer is bound to {self.host} without TLS; the password is sent in clear text. "
                "Set BLOG_TLS_CERT/BLOG_TLS_KEY or keep BLOG_HOST=127.0.0.1.\n"
            )
        self.port = server.server_address[1]  # resolves port 0 to the one actually bound
        self._server = server
        threading.Thread(target=server.serve_forever, args=(self.POLL_INTERVAL,), daemon=True).start()

    def stop(self) -> None:
        """Stop serving and release the port."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
