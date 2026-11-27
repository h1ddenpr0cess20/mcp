import base64
import http.client
import ssl
from datetime import datetime, timedelta, timezone

import pytest

from blog_client import BlogClient, BlogServer

USERNAME = "owner"
PASSWORD = "correct horse battery staple"


@pytest.fixture
def blog(tmp_path):
    """A BlogClient backed by an empty database in a temp directory."""
    return BlogClient(data_dir=str(tmp_path / "blog"))


@pytest.fixture
def clock(monkeypatch):
    """Freeze blog timestamps; call the returned function to move time forward."""
    state = {"now": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)}

    def fake_now():
        return state["now"].strftime("%Y-%m-%dT%H:%M:%SZ")

    def advance(minutes: int = 1):
        state["now"] += timedelta(minutes=minutes)

    monkeypatch.setattr("blog_client.client._now", fake_now)
    return advance


@pytest.fixture
def viewer(blog):
    """A running viewer on an ephemeral port with known credentials."""
    server = BlogServer(
        blog, host="127.0.0.1", port=0, username=USERNAME, password=PASSWORD,
        title="Test Blog", description="Notes for testing",
    )
    server.AUTH_FAIL_DELAY = 0
    server.POLL_INTERVAL = 0.01
    server.start()
    yield server
    server.stop()


def basic_auth(user: str = USERNAME, password: str = PASSWORD) -> dict:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def fetch(server, path: str, headers: dict | None = None, method: str = "GET", authed: bool = True):
    """Make a request to the viewer with the server's own credentials. Returns (status, headers, body_text)."""
    all_headers = {**(basic_auth(server.username, server.password) if authed else {}), **(headers or {})}
    if server.scheme == "https":
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        conn = http.client.HTTPSConnection("127.0.0.1", server.port, timeout=10, context=context)
    else:
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
    try:
        conn.request(method, path, headers=all_headers)
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        return response.status, {k.lower(): v for k, v in response.getheaders()}, body
    finally:
        conn.close()
