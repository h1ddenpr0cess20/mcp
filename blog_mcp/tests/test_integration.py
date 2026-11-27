"""The MCP server against the real blog application, over real HTTP.

Needs the blog application next to this package and its dependencies (see ../blog/requirements.txt);
skipped when either is missing. FastMCP already pulls in most of those dependencies, so these usually run.
"""

import asyncio
import http.client
import importlib.util
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlencode

import pytest

pytest.importorskip("markdown_it")
pytest.importorskip("multipart")
BLOG_DIR = Path(__file__).resolve().parents[2] / "blog"
if not (BLOG_DIR / "blog_app").is_dir():
    pytest.skip("the blog application is not next to this package", allow_module_level=True)
sys.path.insert(0, str(BLOG_DIR))

import uvicorn  # noqa: E402
from blog_app import Settings, create_app  # noqa: E402
from fastmcp import Client  # noqa: E402

SERVER_PATH = Path(__file__).resolve().parent.parent / "server.py"
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
       b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class RunningBlog:
    def __init__(self, data_dir, token="integration-token"):
        self.port = free_port()
        self.settings = Settings(data_dir=data_dir, port=self.port, password="integration password", api_token=token)
        self.app = create_app(self.settings)
        self.server = uvicorn.Server(uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="error", access_log=False))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        deadline = time.time() + 10
        while not self.server.started:
            assert time.time() < deadline, "blog did not start"
            time.sleep(0.01)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}"

    def stop(self):
        self.server.should_exit = True
        self.thread.join(timeout=10)

    def get(self, path, logged_in=True):
        headers = {}
        if logged_in:
            conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
            conn.request("POST", "/login", body=urlencode({"username": "owner", "password": "integration password"}),
                         headers={"Content-Type": "application/x-www-form-urlencoded"})
            headers["Cookie"] = conn.getresponse().getheader("set-cookie").split(";")[0]
            conn.close()
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", path, headers=headers)
        response = conn.getresponse()
        return response.status, response.read().decode("utf-8", "replace")


@pytest.fixture
def blog(tmp_path):
    running = RunningBlog(tmp_path / "blog-data")
    yield running
    running.stop()


@pytest.fixture
def mcp_server(blog, monkeypatch, tmp_path):
    monkeypatch.setenv("BLOG_URL", blog.url)
    monkeypatch.setenv("BLOG_API_TOKEN", "integration-token")
    spec = importlib.util.spec_from_file_location("blog_mcp_integration", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop(spec.name, None)


def call(module, name, **arguments):
    async def run():
        async with Client(module.mcp) as client:
            return await client.call_tool(name, arguments, raise_on_error=False)

    return asyncio.run(run())


@pytest.mark.integration
class TestMcpServerWithTheRealBlog:
    def test_a_post_written_through_a_tool_is_on_the_website(self, mcp_server, blog):
        created = call(mcp_server, "create_post", title="Written by a tool", body="Hello **world**", tags=["demo"], publish=True).data
        assert created["url"] == f"{blog.url}/post/written-by-a-tool"
        status, page = blog.get("/post/written-by-a-tool")
        assert status == 200 and "<strong>world</strong>" in page
        assert "Written by a tool" in blog.get("/")[1]

    def test_the_website_asks_anonymous_visitors_to_log_in(self, mcp_server, blog):
        call(mcp_server, "create_post", title="Private", body="secret", publish=True)
        status, page = blog.get("/post/private", logged_in=False)
        assert status == 303 or "secret" not in page

    def test_edits_status_changes_and_deletes_show_up_immediately(self, mcp_server, blog):
        call(mcp_server, "create_post", title="Changing", body="version one", publish=True)
        call(mcp_server, "replace_in_post", slug="changing", find="one", replace="two")
        assert "version two" in blog.get("/post/changing")[1]
        call(mcp_server, "unpublish_post", slug="changing")
        assert "Changing" not in blog.get("/")[1]
        assert call(mcp_server, "delete_post", slug="changing").data["deleted"] is True
        assert blog.get("/post/changing")[0] == 404

    def test_a_post_written_in_the_browser_editor_is_readable_by_a_tool(self, mcp_server, blog):
        blog.app.state.blog.store.create_post("Typed in a browser", "from the editor", publish=True)
        assert call(mcp_server, "get_post", slug="typed-in-a-browser").data["body"] == "from the editor"

    def test_images(self, mcp_server, blog, tmp_path):
        picture = tmp_path / "pic.png"
        picture.write_bytes(PNG)
        uploaded = call(mcp_server, "upload_image", file_path=str(picture), alt_text="dot").data
        call(mcp_server, "create_post", title="With image", body=uploaded["markdown"], publish=True)
        assert uploaded["url"] in blog.get("/post/with-image")[1]
        assert blog.get(uploaded["url"])[0] == 200

    def test_the_blogs_error_messages_come_through(self, mcp_server, blog):
        call(mcp_server, "create_post", title="One", slug="taken")
        assert "already in use" in call(mcp_server, "create_post", title="Two", slug="taken").content[0].text
        assert "not found" in call(mcp_server, "get_post", slug="ghost").content[0].text
        assert "title must not be empty" in call(mcp_server, "create_post", title="  ").content[0].text

    def test_search_and_tags(self, mcp_server, blog):
        call(mcp_server, "create_post", title="Tomato notes", body="Tomatoes need sun.", tags=["garden"], publish=True)
        assert call(mcp_server, "search_posts", query="tomatoes").data["count"] == 1
        assert call(mcp_server, "list_tags").data["tags"] == [{"tag": "garden", "count": 1}]

    def test_info_reflects_the_running_blog(self, mcp_server, blog):
        info = call(mcp_server, "get_blog_info").data
        assert info["blog_running"] is True and info["blog_url"] == blog.url and info["public"] is False

    def test_a_wrong_token_is_refused(self, mcp_server, blog, monkeypatch):
        mcp_server._client.token = "wrong"
        assert "API token" in call(mcp_server, "create_post", title="x").content[0].text
        assert blog.app.state.blog.store.stats()["total"] == 0

    def test_the_blog_keeps_working_when_the_mcp_server_is_gone_and_vice_versa(self, mcp_server, blog):
        call(mcp_server, "create_post", title="Survivor", body="still here", publish=True)
        mcp_server._client.base_url = "http://127.0.0.1:1"  # the blog 'goes down' from the server's point of view
        info = call(mcp_server, "get_blog_info").data
        assert info["blog_running"] is False and "python blog/blog.py" in info["message"]
        assert "still here" in blog.get("/post/survivor")[1]
