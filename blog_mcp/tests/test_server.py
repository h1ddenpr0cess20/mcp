"""Tests for the FastMCP tools in server.py, driven through an in-memory MCP client against a fake blog."""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest
import requests
from fastmcp import Client

from blog_client import BlogClient
from tests.conftest import FakeSession, make_response

SERVER_PATH = Path(__file__).resolve().parent.parent / "server.py"

EXPECTED_TOOLS = {
    "create_post", "get_post", "list_posts", "update_post", "replace_in_post", "publish_post", "unpublish_post",
    "delete_post", "search_posts", "list_tags", "upload_image", "get_blog_info",
    "attach_text", "attach_file", "list_attachments", "read_attachment", "remove_attachment",
}

POST = {"slug": "hello", "title": "Hello", "status": "draft", "tags": [], "url": "http://blog.test/post/hello"}


def load_server(monkeypatch, tmp_path, url="http://127.0.0.1:9901"):
    monkeypatch.setenv("BLOG_URL", url)
    monkeypatch.setenv("BLOG_API_TOKEN", "test-token")
    monkeypatch.setenv("BLOG_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location("blog_mcp_server_under_test", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def srv(monkeypatch, tmp_path):
    module = load_server(monkeypatch, tmp_path)
    yield module
    sys.modules.pop("blog_mcp_server_under_test", None)


@pytest.fixture
def blog(srv):
    """Answer the server's API calls from `blog.reply`; `blog.session` records what it sent."""

    class Fake:
        reply = staticmethod(lambda method, url, kwargs: make_response(200, POST))

    fake = Fake()
    fake.session = FakeSession(lambda m, u, k: fake.reply(m, u, k))
    srv._client = BlogClient(base_url="http://blog.test", token="test-token", session=fake.session)
    return fake


def call(module, name, **arguments):
    async def run():
        async with Client(module.mcp) as client:
            return await client.call_tool(name, arguments, raise_on_error=False)

    return asyncio.run(run())


def ok(module, name, **arguments):
    result = call(module, name, **arguments)
    assert not result.is_error, result.content[0].text
    return result.data


def failure(module, name, **arguments) -> str:
    result = call(module, name, **arguments)
    assert result.is_error
    return result.content[0].text


class TestToolSurface:
    @pytest.mark.integration
    def test_registered_tools(self, srv):
        async def names():
            async with Client(srv.mcp) as client:
                return {tool.name for tool in await client.list_tools()}

        assert asyncio.run(names()) == EXPECTED_TOOLS

    @pytest.mark.integration
    def test_every_tool_is_documented_and_schemas_stay_simple(self, srv):
        async def tools():
            async with Client(srv.mcp) as client:
                return await client.list_tools()

        for tool in asyncio.run(tools()):
            assert tool.description and len(tool.description) > 20, tool.name
            assert "anyOf" not in json.dumps(tool.inputSchema), tool.name  # local-LLM friendly: no null unions

    @pytest.mark.integration
    def test_importing_the_server_serves_nothing_and_makes_no_requests(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(requests.Session, "request", lambda *a, **k: calls.append(a))
        module = load_server(monkeypatch, tmp_path)
        try:
            assert calls == []
            assert not hasattr(module, "_web") and not hasattr(module, "_site")
        finally:
            sys.modules.pop("blog_mcp_server_under_test", None)

    @pytest.mark.integration
    def test_the_server_owns_no_storage(self, srv, tmp_path):
        assert list(tmp_path.iterdir()) == []  # no database, no password file: the blog owns all of that


class TestToolsCallTheBlog:
    @pytest.mark.integration
    def test_create_post(self, srv, blog):
        result = ok(srv, "create_post", title="Hello", body="Body", tags=["a"], slug="hello", summary="S", publish=True)
        assert result["url"] == "http://blog.test/post/hello"
        assert blog.session.last["json"] == {
            "title": "Hello", "body": "Body", "tags": ["a"], "slug": "hello", "summary": "S", "publish": True,
        }

    @pytest.mark.integration
    def test_get_and_list(self, srv, blog):
        ok(srv, "get_post", slug="hello")
        assert blog.session.last["url"] == "http://blog.test/api/v1/posts/hello"
        blog.reply = lambda m, u, k: make_response(200, {"posts": [POST], "total": 1, "limit": 20, "offset": 0})
        assert ok(srv, "list_posts", status="draft", tag="x", limit=5, offset=2)["total"] == 1
        assert blog.session.last["params"] == {"status": "draft", "tag": "x", "limit": 5, "offset": 2}

    @pytest.mark.integration
    @pytest.mark.parametrize("arguments,sent", [
        ({"title": "New"}, {"title": "New"}),
        ({"body": "B"}, {"body": "B"}),
        ({"summary": "S"}, {"summary": "S"}),
        ({"tags": ["a", "b"]}, {"tags": ["a", "b"]}),
        ({"clear_tags": True}, {"tags": []}),
        ({"tags": ["z"], "clear_tags": True}, {"tags": ["z"]}),
        ({"new_slug": "n"}, {"slug": "n"}),
        ({"title": "T", "new_slug": "n", "tags": ["x"]}, {"title": "T", "slug": "n", "tags": ["x"]}),
    ])
    def test_update_post_sends_only_what_was_asked_for(self, srv, blog, arguments, sent):
        ok(srv, "update_post", slug="hello", **arguments)
        assert (blog.session.last["method"], blog.session.last["url"]) == ("PATCH", "http://blog.test/api/v1/posts/hello")
        assert blog.session.last["json"] == sent

    @pytest.mark.integration
    def test_update_with_nothing_asked_for_is_left_to_the_blog_to_reject(self, srv, blog):
        blog.reply = lambda m, u, k: make_response(400, {"error": "Nothing to update: pass at least one field to change"})
        assert "Nothing to update" in failure(srv, "update_post", slug="hello")

    @pytest.mark.integration
    def test_replace_in_post(self, srv, blog):
        ok(srv, "replace_in_post", slug="hello", find="a", replace="b", replace_all=True)
        assert blog.session.last["url"].endswith("/hello/replace")
        assert blog.session.last["json"] == {"find": "a", "replace": "b", "replace_all": True}

    @pytest.mark.integration
    @pytest.mark.parametrize("tool,suffix", [("publish_post", "/publish"), ("unpublish_post", "/unpublish")])
    def test_publish_and_unpublish(self, srv, blog, tool, suffix):
        ok(srv, tool, slug="hello")
        assert blog.session.last["url"].endswith(f"/hello{suffix}")

    @pytest.mark.integration
    def test_delete_post(self, srv, blog):
        blog.reply = lambda m, u, k: make_response(200, {"slug": "hello", "deleted": True})
        assert ok(srv, "delete_post", slug="hello") == {"slug": "hello", "deleted": True}
        blog.reply = lambda m, u, k: make_response(404, {"error": "Post 'hello' not found"})
        assert ok(srv, "delete_post", slug="hello") == {"slug": "hello", "deleted": False}

    @pytest.mark.integration
    def test_search_and_tags(self, srv, blog):
        blog.reply = lambda m, u, k: make_response(200, {"query": "q", "posts": [], "count": 0})
        ok(srv, "search_posts", query="two words", status="published", limit=3)
        assert blog.session.last["params"] == {"q": "two words", "status": "published", "limit": 3}
        blog.reply = lambda m, u, k: make_response(200, {"tags": [{"tag": "x", "count": 2}], "count": 1})
        assert ok(srv, "list_tags", status="published")["tags"][0]["count"] == 2

    @pytest.mark.integration
    def test_slugs_with_special_characters_cannot_change_the_path(self, srv, blog):
        ok(srv, "get_post", slug="../admin?x=1")
        assert blog.session.last["url"] == "http://blog.test/api/v1/posts/..%2Fadmin%3Fx%3D1"


class TestUploadImage:
    @pytest.mark.integration
    def test_returns_markdown_ready_to_paste(self, srv, blog, tmp_path):
        picture = tmp_path / "p.png"
        picture.write_bytes(b"x")
        blog.reply = lambda m, u, k: make_response(201, {"url": "/media/abc.png", "absolute_url": "http://blog.test/media/abc.png"})
        result = ok(srv, "upload_image", file_path=str(picture), alt_text="A sunset")
        assert result["markdown"] == "![A sunset](/media/abc.png)"

    @pytest.mark.integration
    def test_alt_text_cannot_break_the_markdown(self, srv, blog, tmp_path):
        picture = tmp_path / "p.png"
        picture.write_bytes(b"x")
        blog.reply = lambda m, u, k: make_response(201, {"url": "/media/abc.png", "absolute_url": "x"})
        result = ok(srv, "upload_image", file_path=str(picture), alt_text="a](http://evil.example)[b\nline")
        assert result["markdown"] == "![a(http://evil.example)b line](/media/abc.png)"

    @pytest.mark.integration
    def test_missing_file(self, srv, blog):
        assert "No file at /nope.png" in failure(srv, "upload_image", file_path="/nope.png")

    @pytest.mark.integration
    def test_the_blog_refusing_the_file_is_passed_on(self, srv, blog, tmp_path):
        text = tmp_path / "t.png"
        text.write_text("not an image")
        blog.reply = lambda m, u, k: make_response(400, {"error": "Only PNG, JPEG, GIF, and WebP images can be uploaded"})
        assert "PNG, JPEG, GIF, and WebP" in failure(srv, "upload_image", file_path=str(text))


class TestErrors:
    @pytest.mark.integration
    @pytest.mark.parametrize("status,error", [
        (404, "Post 'x' not found"), (409, "Slug 'x' is already in use"), (400, "title must not be empty"),
    ])
    def test_the_blogs_message_reaches_the_model_without_a_traceback(self, srv, blog, status, error):
        blog.reply = lambda m, u, k: make_response(status, {"error": error})
        text = failure(srv, "create_post", title="x")
        assert error in text and "Traceback" not in text

    @pytest.mark.integration
    def test_a_rejected_token(self, srv, blog):
        blog.reply = lambda m, u, k: make_response(401, {"error": "Missing or invalid API token"})
        assert "BLOG_API_TOKEN" in failure(srv, "get_post", slug="x")

    @pytest.mark.integration
    def test_a_down_blog_tells_you_how_to_start_it(self, srv, blog):
        blog.reply = lambda m, u, k: requests.exceptions.ConnectionError("refused")
        assert "python blog_mcp/blog/blog.py" in failure(srv, "create_post", title="x")


class TestBlogInfo:
    @pytest.mark.integration
    def test_running(self, srv, blog):
        counts = {"total": 3, "published": 2, "drafts": 1, "tags": 4}
        blog.reply = lambda m, u, k: make_response(200, {"title": "My Blog", "description": "d", "public": False,
                                                         "url": "http://blog.test", "posts": counts})
        info = ok(srv, "get_blog_info")
        assert info["blog_running"] is True and info["title"] == "My Blog" and info["posts"]["drafts"] == 1
        assert info["public"] is False and info["blog_url"] == "http://blog.test"

    @pytest.mark.integration
    def test_not_running_is_an_answer_not_a_failure(self, srv, blog):
        blog.reply = lambda m, u, k: requests.exceptions.ConnectionError("refused")
        info = ok(srv, "get_blog_info")
        assert info["blog_running"] is False and info["blog_url"] == "http://blog.test"
        assert "python blog_mcp/blog/blog.py" in info["message"]

    @pytest.mark.integration
    def test_a_wrong_token_is_still_an_error(self, srv, blog):
        blog.reply = lambda m, u, k: make_response(401, {"error": "x"})
        assert "API token" in failure(srv, "get_blog_info")

    @pytest.mark.integration
    def test_never_reveals_the_token(self, srv, blog):
        blog.reply = lambda m, u, k: make_response(200, {"title": "t", "description": "", "public": False, "url": "http://blog.test",
                                                         "posts": {"total": 0, "published": 0, "drafts": 0, "tags": 0}})
        assert "test-token" not in json.dumps(ok(srv, "get_blog_info"))


class TestStartupWarning:
    @pytest.mark.integration
    def test_plain_http_to_another_machine_warns_about_the_token(self, monkeypatch, tmp_path, capsys):
        load_server(monkeypatch, tmp_path, url="http://blog.example.com:9901")
        sys.modules.pop("blog_mcp_server_under_test", None)
        assert "clear text" in capsys.readouterr().err

    @pytest.mark.integration
    @pytest.mark.parametrize("url", ["http://127.0.0.1:9901", "http://localhost:9901", "https://blog.example.com"])
    def test_loopback_and_https_do_not_warn(self, monkeypatch, tmp_path, capsys, url):
        load_server(monkeypatch, tmp_path, url=url)
        sys.modules.pop("blog_mcp_server_under_test", None)
        assert "WARNING" not in capsys.readouterr().err


class TestAttachmentTools:
    ATTACHED = {"id": "c" * 32, "filename": "analysis.py", "size": 12, "content_type": "text/x-python", "is_text": True,
                "replaced": False, "url": "http://blog.test/files/" + "c" * 32}

    @pytest.mark.integration
    def test_attach_text_sends_the_text_as_a_utf8_file_and_returns_a_link(self, srv, blog):
        blog.reply = lambda m, u, k: make_response(201, dict(self.ATTACHED))
        result = ok(srv, "attach_text", slug="my-post", filename="analysis.py", content="print('héllo 日本語')\n")
        assert (blog.session.last["method"], blog.session.last["url"]) == ("POST", "http://blog.test/api/v1/posts/my-post/attachments")
        assert blog.session.last["files"] == {"file": ("analysis.py", "print('héllo 日本語')\n".encode())}
        assert result["markdown"] == f"[analysis.py](/files/{'c' * 32})" and result["url"].endswith("c" * 32)

    @pytest.mark.integration
    def test_the_markdown_link_cannot_be_broken_by_the_file_name(self, srv, blog):
        blog.reply = lambda m, u, k: make_response(201, {**self.ATTACHED, "filename": "a](http://evil.example)[b.txt"})
        result = ok(srv, "attach_text", slug="p", filename="whatever", content="x")
        assert result["markdown"] == f"[a(http://evil.example)b.txt](/files/{'c' * 32})"

    @pytest.mark.integration
    def test_attach_text_with_empty_content_attaches_an_empty_file(self, srv, blog):
        blog.reply = lambda m, u, k: make_response(201, {**self.ATTACHED, "size": 0})
        ok(srv, "attach_text", slug="p", filename="__init__.py", content="")
        assert blog.session.last["files"]["file"] == ("__init__.py", b"")

    @pytest.mark.integration
    def test_attach_file(self, srv, blog, tmp_path):
        local = tmp_path / "data.csv"
        local.write_bytes(b"a,b\n")
        blog.reply = lambda m, u, k: make_response(201, {**self.ATTACHED, "filename": "data.csv"})
        result = ok(srv, "attach_file", slug="p", file_path=str(local), filename="renamed.csv")
        assert blog.session.last["files"]["file"][0] == "renamed.csv" and result["markdown"].startswith("[data.csv](")

    @pytest.mark.integration
    def test_attach_file_missing(self, srv, blog):
        assert "No file at /nope.bin" in failure(srv, "attach_file", slug="p", file_path="/nope.bin")

    @pytest.mark.integration
    def test_list_read_and_remove(self, srv, blog):
        blog.reply = lambda m, u, k: make_response(200, {"attachments": [self.ATTACHED], "count": 1})
        assert ok(srv, "list_attachments", slug="p")["count"] == 1
        blog.reply = lambda m, u, k: make_response(200, {**self.ATTACHED, "content": "print(1)", "truncated": False, "post_slug": "p"})
        read = ok(srv, "read_attachment", attachment_id="c" * 32, max_bytes=100)
        assert read["content"] == "print(1)" and blog.session.last["params"] == {"max_bytes": 100}
        blog.reply = lambda m, u, k: make_response(200, {"slug": "p", "id": "c" * 32, "deleted": True})
        assert ok(srv, "remove_attachment", slug="p", attachment_id="c" * 32)["deleted"] is True
        assert blog.session.last["method"] == "DELETE"

    @pytest.mark.integration
    def test_read_attachment_defaults_to_the_blogs_own_limit(self, srv, blog):
        ok(srv, "read_attachment", attachment_id="c" * 32)
        assert blog.session.last["params"] is None

    @pytest.mark.integration
    @pytest.mark.parametrize("status,error,tool,arguments", [
        (404, "Post 'ghost' not found", "attach_text", {"slug": "ghost", "filename": "a.txt", "content": "x"}),
        (400, "A post can have at most 50 attachments", "attach_text", {"slug": "p", "filename": "a.txt", "content": "x"}),
        (413, "Files can be at most 25 MB", "attach_text", {"slug": "p", "filename": "a.txt", "content": "x"}),
        (404, "Attachment not found", "read_attachment", {"attachment_id": "0" * 32}),
        (404, "That file is not attached to this post", "remove_attachment", {"slug": "p", "attachment_id": "0" * 32}),
    ])
    def test_the_blogs_messages_reach_the_model(self, srv, blog, status, error, tool, arguments):
        blog.reply = lambda m, u, k: make_response(status, {"error": error})
        text = failure(srv, tool, **arguments)
        assert error in text and "Traceback" not in text
