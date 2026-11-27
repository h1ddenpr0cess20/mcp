"""Tests for the FastMCP tool layer in server.py, driven through an in-memory MCP client."""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from fastmcp import Client

from blog_client import BlogServer
from tests.conftest import fetch

SERVER_PATH = Path(__file__).resolve().parent.parent / "server.py"

EXPECTED_TOOLS = {
    "create_post", "get_post", "list_posts", "update_post", "replace_in_post", "publish_post",
    "unpublish_post", "delete_post", "search_posts", "list_tags", "get_blog_info",
}


@pytest.fixture
def srv(tmp_path, monkeypatch):
    """server.py imported fresh, pointed at a temp blog with the viewer on an ephemeral port."""
    monkeypatch.setenv("BLOG_DIR", str(tmp_path / "blog"))
    monkeypatch.setenv("BLOG_PORT", "0")
    monkeypatch.delenv("BLOG_PASSWORD", raising=False)
    monkeypatch.setattr(BlogServer, "POLL_INTERVAL", 0.01)  # server.py starts the viewer on import
    spec = importlib.util.spec_from_file_location("blog_server_under_test", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module._web.AUTH_FAIL_DELAY = 0
    yield module
    module._web.stop()
    sys.modules.pop(spec.name, None)


def call(module, name: str, **arguments):
    async def run():
        async with Client(module.mcp) as client:
            return await client.call_tool(name, arguments, raise_on_error=False)

    return asyncio.run(run())


def ok(module, name: str, **arguments) -> dict:
    result = call(module, name, **arguments)
    assert not result.is_error, result.content[0].text
    return result.data


def error_text(module, name: str, **arguments) -> str:
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
    def test_every_tool_is_documented(self, srv):
        async def tools():
            async with Client(srv.mcp) as client:
                return await client.list_tools()

        for tool in asyncio.run(tools()):
            assert tool.description and len(tool.description) > 20, tool.name

    @pytest.mark.integration
    def test_tool_schemas_avoid_null_unions_for_local_llm_compatibility(self, srv):
        async def tools():
            async with Client(srv.mcp) as client:
                return await client.list_tools()

        for tool in asyncio.run(tools()):
            assert "anyOf" not in json.dumps(tool.inputSchema), tool.name


class TestPostLifecycle:
    @pytest.mark.integration
    def test_create_publish_edit_unpublish_delete(self, srv):
        created = ok(srv, "create_post", title="Hello World", body="First draft.", tags=["Intro"])
        assert created["slug"] == "hello-world"
        assert created["status"] == "draft"
        assert created["tags"] == ["intro"]
        assert created["url"] == f"{srv._web.base_url}/post/hello-world"

        assert ok(srv, "publish_post", slug="hello-world")["status"] == "published"
        replaced = ok(srv, "replace_in_post", slug="hello-world", find="First draft", replace="Final text")
        assert (replaced["body"], replaced["replacements"]) == ("Final text.", 1)
        assert ok(srv, "get_post", slug="hello-world")["body"] == "Final text."
        assert ok(srv, "unpublish_post", slug="hello-world")["status"] == "draft"
        assert ok(srv, "delete_post", slug="hello-world") == {"slug": "hello-world", "deleted": True}
        assert ok(srv, "delete_post", slug="hello-world") == {"slug": "hello-world", "deleted": False}

    @pytest.mark.integration
    def test_create_with_publish_flag_and_explicit_fields(self, srv):
        post = ok(srv, "create_post", title="T", body="B", slug="custom", summary="S", publish=True)
        assert (post["slug"], post["summary"], post["status"]) == ("custom", "S", "published")

    @pytest.mark.integration
    def test_update_post_keeps_unspecified_fields(self, srv):
        ok(srv, "create_post", title="Original", body="Body", tags=["a", "b"])
        post = ok(srv, "update_post", slug="original", title="Renamed")
        assert (post["title"], post["body"], post["tags"]) == ("Renamed", "Body", ["a", "b"])

    @pytest.mark.integration
    def test_update_post_tag_handling(self, srv):
        ok(srv, "create_post", title="T", tags=["a", "b"])
        assert ok(srv, "update_post", slug="t", tags=["c"])["tags"] == ["c"]
        assert ok(srv, "update_post", slug="t", clear_tags=True)["tags"] == []

    @pytest.mark.integration
    def test_tags_win_over_clear_tags(self, srv):
        ok(srv, "create_post", title="T", tags=["a"])
        assert ok(srv, "update_post", slug="t", tags=["z"], clear_tags=True)["tags"] == ["z"]

    @pytest.mark.integration
    def test_update_post_can_rename_slug(self, srv):
        ok(srv, "create_post", title="T")
        post = ok(srv, "update_post", slug="t", new_slug="renamed")
        assert post["slug"] == "renamed"
        assert post["url"].endswith("/post/renamed")

    @pytest.mark.integration
    def test_list_posts(self, srv):
        ok(srv, "create_post", title="Draft")
        ok(srv, "create_post", title="Live", publish=True, tags=["x"])
        everything = ok(srv, "list_posts")
        assert everything["total"] == 2
        assert all("url" in post and "body" not in post for post in everything["posts"])
        assert [p["slug"] for p in ok(srv, "list_posts", status="published")["posts"]] == ["live"]
        assert [p["slug"] for p in ok(srv, "list_posts", tag="x")["posts"]] == ["live"]
        assert len(ok(srv, "list_posts", limit=1)["posts"]) == 1

    @pytest.mark.integration
    def test_search_and_tags(self, srv):
        ok(srv, "create_post", title="Soup", body="Simmer the carrots gently.", tags=["cooking"], publish=True)
        result = ok(srv, "search_posts", query="carrots")
        assert result["count"] == 1
        assert "carrots" in result["posts"][0]["snippet"]
        assert result["posts"][0]["url"].endswith("/post/soup")
        assert ok(srv, "list_tags")["tags"] == [{"tag": "cooking", "count": 1}]


class TestErrors:
    @pytest.mark.integration
    @pytest.mark.parametrize("name,arguments,message", [
        ("get_post", {"slug": "ghost"}, "not found"),
        ("publish_post", {"slug": "ghost"}, "not found"),
        ("unpublish_post", {"slug": "ghost"}, "not found"),
        ("update_post", {"slug": "ghost", "title": "x"}, "not found"),
        ("replace_in_post", {"slug": "ghost", "find": "a", "replace": "b"}, "not found"),
        ("create_post", {"title": "   "}, "title must not be empty"),
        ("list_posts", {"status": "bogus"}, "status must be"),
        ("search_posts", {"query": ""}, "query must not be empty"),
        ("list_tags", {"status": "bogus"}, "status must be"),
    ])
    def test_expected_failures_are_clean_tool_errors(self, srv, name, arguments, message):
        text = error_text(srv, name, **arguments)
        assert message in text
        assert "Traceback" not in text

    @pytest.mark.integration
    def test_duplicate_slug(self, srv):
        ok(srv, "create_post", title="One", slug="taken")
        assert "already in use" in error_text(srv, "create_post", title="Two", slug="taken")

    @pytest.mark.integration
    def test_update_with_nothing_to_change(self, srv):
        ok(srv, "create_post", title="T")
        assert "Nothing to update" in error_text(srv, "update_post", slug="t")

    @pytest.mark.integration
    def test_ambiguous_replace(self, srv):
        ok(srv, "create_post", title="T", body="aa aa")
        assert "2 times" in error_text(srv, "replace_in_post", slug="t", find="aa", replace="b")
        assert ok(srv, "replace_in_post", slug="t", find="aa", replace="b", replace_all=True)["body"] == "b b"


class TestBlogInfo:
    @pytest.mark.integration
    def test_reports_location_and_counts(self, srv):
        ok(srv, "create_post", title="A", publish=True)
        ok(srv, "create_post", title="B")
        info = ok(srv, "get_blog_info")
        assert info["viewer_url"] == srv._web.base_url
        assert info["viewer_username"] == "owner"
        assert info["data_dir"] == str(srv._client.data_dir)
        assert info["posts"] == {"total": 2, "published": 1, "drafts": 1, "tags": 0}

    @pytest.mark.integration
    def test_never_reveals_the_viewer_password(self, srv):
        password = srv._web.password
        info = ok(srv, "get_blog_info")
        assert password not in json.dumps(info)
        assert info["password_source"].endswith("viewer_password")
        post = ok(srv, "create_post", title="T", body="B")
        assert password not in json.dumps(post)

    @pytest.mark.integration
    def test_configured_password_source_is_named_not_shown(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BLOG_PASSWORD", "hunter2-hunter2")
        monkeypatch.setenv("BLOG_DIR", str(tmp_path / "blog"))
        monkeypatch.setenv("BLOG_PORT", "0")
        monkeypatch.setattr(BlogServer, "POLL_INTERVAL", 0.01)
        spec = importlib.util.spec_from_file_location("blog_server_env_password", SERVER_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        try:
            info = ok(module, "get_blog_info")
            assert info["password_source"] == "BLOG_PASSWORD"
            assert "hunter2" not in json.dumps(info)
        finally:
            module._web.stop()
            sys.modules.pop(spec.name, None)


class TestToolsAndViewerTogether:
    @pytest.mark.integration
    def test_a_post_created_through_a_tool_is_served_at_its_returned_url(self, srv):
        post = ok(srv, "create_post", title="Seen in the viewer", body="Hello from the tool.", publish=True)
        path = post["url"].removeprefix(srv._web.base_url)
        status, _, body = fetch(srv._web, path)
        assert status == 200
        assert "Hello from the tool." in body

    @pytest.mark.integration
    def test_the_returned_url_is_not_readable_without_the_password(self, srv):
        post = ok(srv, "create_post", title="Private", body="secret text", publish=True)
        path = post["url"].removeprefix(srv._web.base_url)
        status, _, body = fetch(srv._web, path, authed=False)
        assert status == 401
        assert "secret text" not in body

    @pytest.mark.integration
    def test_edits_and_unpublishing_show_up_immediately(self, srv):
        ok(srv, "create_post", title="Live", body="version one", publish=True)
        assert "version one" in fetch(srv._web, "/post/live")[2]
        ok(srv, "replace_in_post", slug="live", find="one", replace="two")
        assert "version two" in fetch(srv._web, "/post/live")[2]
        ok(srv, "unpublish_post", slug="live")
        assert "Live" not in fetch(srv._web, "/")[2]
        ok(srv, "delete_post", slug="live")
        assert fetch(srv._web, "/post/live")[0] == 404
