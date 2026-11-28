"""The MCP server against the real blog application, over real HTTP.

Needs the blog application (the `blog` folder inside this package) and its dependencies (see ../blog/requirements.txt);
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
BLOG_DIR = Path(__file__).resolve().parents[1] / "blog"
if not (BLOG_DIR / "blog_app").is_dir():
    pytest.skip("the blog application is not inside this package", allow_module_level=True)
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
    def __init__(self, data_dir, token="integration-token", max_attachment_mb=25):
        self.port = free_port()
        self.settings = Settings(data_dir=data_dir, port=self.port, password="integration password", api_token=token,
                                 max_attachment_mb=max_attachment_mb)
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
        assert info["blog_running"] is False and "python blog_mcp/blog/blog.py" in info["message"]
        assert "still here" in blog.get("/post/survivor")[1]


@pytest.mark.integration
class TestAttachmentsWithTheRealBlog:
    CODE = "def total(values):\n    return sum(values)\n"

    def test_text_attached_by_a_tool_can_be_downloaded_and_read_on_the_blog(self, mcp_server, blog):
        call(mcp_server, "create_post", title="Analysis", body="See the code.", publish=True)
        attached = call(mcp_server, "attach_text", slug="analysis", filename="helpers.py", content=self.CODE).data
        assert attached["replaced"] is False and attached["markdown"] == f"[helpers.py](/files/{attached['id']})"
        status, downloaded = blog.get(f"/files/{attached['id']}")
        assert status == 200 and downloaded == self.CODE
        assert "helpers.py" in blog.get("/post/analysis")[1] and "def total" in blog.get(f"/files/{attached['id']}/view")[1]

    def test_the_markdown_link_works_inside_a_post(self, mcp_server, blog):
        call(mcp_server, "create_post", title="Linked", body="placeholder", publish=True)
        attached = call(mcp_server, "attach_text", slug="linked", filename="tool.sh", content="echo hi\n").data
        call(mcp_server, "update_post", slug="linked", body=f"Grab the {attached['markdown']} script.")
        assert f'href="/files/{attached["id"]}"' in blog.get("/post/linked")[1]

    def test_attaching_the_same_name_again_replaces_it_and_keeps_the_link(self, mcp_server, blog):
        call(mcp_server, "create_post", title="Versions", body="x", publish=True)
        first = call(mcp_server, "attach_text", slug="versions", filename="notes.md", content="version one").data
        second = call(mcp_server, "attach_text", slug="versions", filename="notes.md", content="version two").data
        assert second["id"] == first["id"] and second["replaced"] is True
        assert blog.get(f"/files/{first['id']}")[1] == "version two"
        assert call(mcp_server, "list_attachments", slug="versions").data["count"] == 1

    def test_an_assistant_can_read_back_what_is_attached(self, mcp_server, blog):
        call(mcp_server, "create_post", title="Readable", body="x", publish=True)
        attached = call(mcp_server, "attach_text", slug="readable", filename="data.csv", content="a,b\n1,2\n").data
        read = call(mcp_server, "read_attachment", attachment_id=attached["id"]).data
        assert (read["content"], read["truncated"], read["post_slug"]) == ("a,b\n1,2\n", False, "readable")
        short = call(mcp_server, "read_attachment", attachment_id=attached["id"], max_bytes=3).data
        assert (short["content"], short["truncated"]) == ("a,b", True)

    def test_a_local_file_can_be_attached_and_a_binary_one_reads_as_details_only(self, mcp_server, blog, tmp_path):
        call(mcp_server, "create_post", title="Files", body="x", publish=True)
        local = tmp_path / "blob.bin"
        local.write_bytes(bytes(range(256)))
        attached = call(mcp_server, "attach_file", slug="files", file_path=str(local)).data
        assert attached["filename"] == "blob.bin" and attached["is_text"] is False and "view_url" not in attached
        read = call(mcp_server, "read_attachment", attachment_id=attached["id"]).data
        assert read["content"] is None and read["size"] == 256

    def test_removing_a_file(self, mcp_server, blog):
        call(mcp_server, "create_post", title="Tidy", body="x", publish=True)
        attached = call(mcp_server, "attach_text", slug="tidy", filename="a.txt", content="x").data
        assert call(mcp_server, "remove_attachment", slug="tidy", attachment_id=attached["id"]).data["deleted"] is True
        assert blog.get(f"/files/{attached['id']}")[0] == 404
        assert "not attached" in call(mcp_server, "remove_attachment", slug="tidy", attachment_id=attached["id"]).content[0].text

    def test_a_post_reports_its_attachments(self, mcp_server, blog):
        call(mcp_server, "create_post", title="Counted", body="x", publish=True)
        call(mcp_server, "attach_text", slug="counted", filename="a.txt", content="x")
        post = call(mcp_server, "get_post", slug="counted").data
        assert post["attachment_count"] == 1 and post["attachments"][0]["filename"] == "a.txt"
        assert call(mcp_server, "list_posts").data["posts"][0]["attachment_count"] == 1

    def test_a_hostile_file_name_is_cleaned_by_the_blog(self, mcp_server, blog):
        call(mcp_server, "create_post", title="Hostile", body="x", publish=True)
        attached = call(mcp_server, "attach_text", slug="hostile", filename="../../etc/passwd", content="x").data
        assert attached["filename"] == "passwd"

    def test_an_unknown_post_is_a_clear_error(self, mcp_server, blog):
        assert "not found" in call(mcp_server, "attach_text", slug="ghost", filename="a.txt", content="x").content[0].text

    def test_the_blogs_size_limit_is_explained(self, tmp_path, monkeypatch):
        small = RunningBlog(tmp_path / "small-blog", max_attachment_mb=1)
        try:
            monkeypatch.setenv("BLOG_URL", small.url)
            monkeypatch.setenv("BLOG_API_TOKEN", "integration-token")
            spec = importlib.util.spec_from_file_location("blog_mcp_small", SERVER_PATH)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            call(module, "create_post", title="Host", body="x", publish=True)
            message = call(module, "attach_text", slug="host", filename="big.txt", content="x" * (1024 * 1024 + 10)).content[0].text
            assert "at most 1 MB" in message or "too large" in message
            assert small.app.state.blog.store.list_attachments("host") == []
            sys.modules.pop(spec.name, None)
        finally:
            small.stop()
