"""Shared test setup: a real blog served by uvicorn on a free port, and a tiny stdlib HTTP client with cookies.

Tests talk to the blog over real HTTP, so they exercise exactly what runs in production and need
no test-only dependencies.
"""

import http.client
import itertools
import json
import re
import socket
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import pytest
import uvicorn

from blog_app import BlogStore, Settings, create_app

PASSWORD = "correct horse battery staple"
API_TOKEN = "test-api-token-0123456789abcdef"
USERNAME = "owner"

# A minimal valid 1x1 PNG, JPEG-signature, GIF, and WebP header for upload tests.
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
       b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82")
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
GIF = b"GIF89a" + b"\x00" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 32


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Response:
    def __init__(self, status: int, headers: list[tuple[str, str]], body: bytes):
        self.status = status
        self.raw_headers = headers
        self.headers = {name.lower(): value for name, value in headers}
        self.body = body

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.body)

    @property
    def location(self) -> str | None:
        return self.headers.get("location")

    def set_cookies(self) -> list[str]:
        return [value for name, value in self.raw_headers if name.lower() == "set-cookie"]


class Browser:
    """A minimal HTTP client with a cookie jar. It never follows redirects, so tests see every step."""

    def __init__(self, host: str, port: int):
        self.host, self.port = host, port
        self.cookies: dict[str, str] = {}

    def request(self, method: str, path: str, *, headers: dict | None = None, body: bytes | None = None,
                form: dict | None = None, json_body=None, files: dict | None = None) -> Response:
        all_headers = dict(headers or {})
        if form is not None:
            body = urlencode(form).encode()
            all_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        elif json_body is not None:
            body = json.dumps(json_body).encode()
            all_headers.setdefault("Content-Type", "application/json")
        elif files is not None:
            boundary = uuid.uuid4().hex
            parts = []
            for field, (filename, content) in files.items():
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
                             f"Content-Type: application/octet-stream\r\n\r\n".encode() + content + b"\r\n")
            body = b"".join(parts) + f"--{boundary}--\r\n".encode()
            all_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        if self.cookies:
            all_headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        conn = http.client.HTTPConnection(self.host, self.port, timeout=15)
        try:
            conn.request(method, path, body=body, headers=all_headers)
            raw = conn.getresponse()
            response = Response(raw.status, raw.getheaders(), raw.read())
        finally:
            conn.close()
        self._store_cookies(response)
        return response

    def _store_cookies(self, response: Response) -> None:
        for header in response.set_cookies():
            pair, *attrs = [part.strip() for part in header.split(";")]
            name, _, value = pair.partition("=")
            expired = any(a.lower().startswith("max-age=") and a.split("=")[1].strip() in ("0", "-1") for a in attrs)
            if expired or value in ("", '""'):
                self.cookies.pop(name, None)
            else:
                self.cookies[name] = value

    def get(self, path: str, **kw) -> Response:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw) -> Response:
        return self.request("POST", path, **kw)

    def csrf(self, path: str = "/admin/new") -> str:
        """The CSRF token the blog embeds in a logged-in page."""
        match = re.search(r'name="csrf" value="([^"]+)"', self.get(path).text)
        assert match, f"no CSRF token on {path}"
        return match.group(1)

    def api(self, method: str, path: str, token: str | None = API_TOKEN, **kw) -> Response:
        headers = dict(kw.pop("headers", {}))
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        return self.request(method, path, headers=headers, **kw)


class RunningBlog:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.app = create_app(settings)
        self.blog = self.app.state.blog
        self.blog.login_delay = 0
        self.port = settings.port
        self.url = f"http://127.0.0.1:{self.port}"
        config = uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="error", access_log=False)
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        deadline = time.time() + 10
        while not self._server.started:
            if time.time() > deadline:
                raise RuntimeError("test blog did not start")
            time.sleep(0.01)

    @property
    def store(self) -> BlogStore:
        return self.blog.store

    def browser(self) -> Browser:
        return Browser("127.0.0.1", self.port)

    def admin(self) -> Browser:
        """A browser already logged in as the owner."""
        browser = self.browser()
        response = browser.post("/login", form={"username": USERNAME, "password": PASSWORD, "next": "/admin"})
        assert response.status == 303, response.text
        return browser

    def stop(self) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=10)


@pytest.fixture
def blog(tmp_path):
    """A BlogStore on an empty database in a temp directory."""
    return BlogStore(tmp_path / "store")


@pytest.fixture
def clock(monkeypatch):
    """Freeze blog timestamps; call the returned function to move time forward."""
    state = {"now": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)}

    def fake_now():
        return state["now"].strftime("%Y-%m-%dT%H:%M:%SZ")

    def advance(minutes: int = 1):
        state["now"] += timedelta(minutes=minutes)

    monkeypatch.setattr("blog_app.store._now", fake_now)
    return advance


_counter = itertools.count()


@pytest.fixture
def make_site(tmp_path):
    """Factory for running blogs; each gets its own data directory and port. All are stopped afterwards."""
    running: list[RunningBlog] = []

    def make(**overrides) -> RunningBlog:
        options = {"data_dir": tmp_path / f"site{next(_counter)}", "port": free_port(), "title": "Test Blog",
                   "description": "Notes for testing", "username": USERNAME, "password": PASSWORD, "api_token": API_TOKEN}
        site = RunningBlog(Settings(**{**options, **overrides}))
        running.append(site)
        return site

    yield make
    for site in running:
        site.stop()


@pytest.fixture
def site(make_site):
    """A private blog (the default): everything needs a login."""
    return make_site()


@pytest.fixture
def public_site(make_site):
    """A blog whose published posts anyone can read."""
    return make_site(public=True)


@pytest.fixture
def admin(site):
    return site.admin()
