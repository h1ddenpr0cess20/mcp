"""Tests for BlogClient: how it talks to the blog's API, and how it reports problems."""

import pytest
import requests
from fastmcp.exceptions import ToolError

from blog_client import BlogClient, BlogError, BlogUnreachable
from tests.conftest import make_response


class TestConfiguration:
    @pytest.mark.unit
    def test_defaults(self, monkeypatch, tmp_path):
        for name in ("BLOG_URL", "BLOG_API_TOKEN", "BLOG_TIMEOUT", "BLOG_VERIFY_TLS"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("BLOG_DIR", str(tmp_path))
        client = BlogClient()
        assert (client.base_url, client.token, client.timeout, client.verify_tls) == ("http://127.0.0.1:9901", "", 30.0, True)

    @pytest.mark.unit
    def test_environment(self, monkeypatch):
        monkeypatch.setenv("BLOG_URL", "https://blog.example.com/")
        monkeypatch.setenv("BLOG_API_TOKEN", "from-env")
        monkeypatch.setenv("BLOG_TIMEOUT", "5")
        monkeypatch.setenv("BLOG_VERIFY_TLS", "false")
        client = BlogClient()
        assert (client.base_url, client.token, client.timeout, client.verify_tls) == ("https://blog.example.com", "from-env", 5.0, False)

    @pytest.mark.unit
    @pytest.mark.parametrize("value,expected", [
        ("true", True), ("1", True), ("", True), ("false", False), ("0", False), ("no", False), ("off", False),
    ])
    def test_tls_verification_flag(self, monkeypatch, value, expected):
        monkeypatch.setenv("BLOG_VERIFY_TLS", value)
        assert BlogClient(token="t").verify_tls is expected

    @pytest.mark.unit
    def test_token_is_found_in_the_blogs_data_directory(self, monkeypatch, tmp_path):
        monkeypatch.delenv("BLOG_API_TOKEN", raising=False)
        monkeypatch.setenv("BLOG_DIR", str(tmp_path))
        (tmp_path / "api_token").write_text("generated-token\n")
        assert BlogClient().token == "generated-token"

    @pytest.mark.unit
    def test_an_explicit_token_beats_the_file(self, monkeypatch, tmp_path):
        monkeypatch.setenv("BLOG_API_TOKEN", "explicit")
        monkeypatch.setenv("BLOG_DIR", str(tmp_path))
        (tmp_path / "api_token").write_text("from-file")
        assert BlogClient().token == "explicit"

    @pytest.mark.unit
    def test_missing_token_fails_helpfully_on_use_not_on_startup(self, make_client):
        client, session = make_client(token="")
        client.token = ""
        with pytest.raises(BlogError, match="No blog API token"):
            client.info()
        assert session.calls == []


class TestRequestShape:
    @pytest.mark.unit
    def test_every_request_is_authenticated_and_hardened(self, make_client):
        client, session = make_client(timeout=7, verify_tls=False)
        client.info()
        call = session.last
        assert call["method"] == "GET" and call["url"] == "http://blog.test/api/v1/info"
        assert call["headers"] == {"Authorization": "Bearer test-token"}
        assert call["timeout"] == 7 and call["verify"] is False
        assert call["allow_redirects"] is False  # the token must never follow a redirect elsewhere

    @pytest.mark.unit
    def test_create_post(self, make_client):
        client, session = make_client()
        client.create_post("T", "body", tags=["a"], slug="s", summary="sum", publish=True)
        assert (session.last["method"], session.last["url"]) == ("POST", "http://blog.test/api/v1/posts")
        assert session.last["json"] == {"title": "T", "body": "body", "tags": ["a"], "slug": "s", "summary": "sum", "publish": True}

    @pytest.mark.unit
    def test_create_post_defaults(self, make_client):
        client, session = make_client()
        client.create_post("T")
        assert session.last["json"] == {"title": "T", "body": "", "tags": [], "slug": "", "summary": "", "publish": False}

    @pytest.mark.unit
    def test_get_post(self, make_client):
        client, session = make_client()
        client.get_post("my-post")
        assert (session.last["method"], session.last["url"]) == ("GET", "http://blog.test/api/v1/posts/my-post")

    @pytest.mark.unit
    @pytest.mark.parametrize("slug,encoded", [
        ("a/b", "a%2Fb"), ("a?b=c", "a%3Fb%3Dc"), ("../admin", "..%2Fadmin"), ("a b", "a%20b"), ("a#b", "a%23b"),
    ])
    def test_slugs_cannot_alter_the_request_path(self, make_client, slug, encoded):
        client, session = make_client()
        client.get_post(slug)
        assert session.last["url"] == f"http://blog.test/api/v1/posts/{encoded}"

    @pytest.mark.unit
    def test_list_posts(self, make_client):
        client, session = make_client()
        client.list_posts(status="draft", tag="x", limit=5, offset=10)
        assert session.last["params"] == {"status": "draft", "tag": "x", "limit": 5, "offset": 10}

    @pytest.mark.unit
    def test_update_sends_only_the_fields_given(self, make_client):
        client, session = make_client()
        client.update_post("p", title="New")
        assert (session.last["method"], session.last["url"]) == ("PATCH", "http://blog.test/api/v1/posts/p")
        assert session.last["json"] == {"title": "New"}

    @pytest.mark.unit
    def test_update_distinguishes_empty_from_absent(self, make_client):
        client, session = make_client()
        client.update_post("p", tags=[], summary="", new_slug="n")
        assert session.last["json"] == {"tags": [], "summary": "", "slug": "n"}

    @pytest.mark.unit
    def test_replace(self, make_client):
        client, session = make_client()
        client.replace_in_post("p", "a", "b", replace_all=True)
        assert (session.last["method"], session.last["url"]) == ("POST", "http://blog.test/api/v1/posts/p/replace")
        assert session.last["json"] == {"find": "a", "replace": "b", "replace_all": True}

    @pytest.mark.unit
    @pytest.mark.parametrize("status,action", [("published", "publish"), ("draft", "unpublish")])
    def test_status_changes(self, make_client, status, action):
        client, session = make_client()
        client.set_status("p", status)
        assert (session.last["method"], session.last["url"]) == ("POST", f"http://blog.test/api/v1/posts/p/{action}")

    @pytest.mark.unit
    def test_invalid_status_never_reaches_the_blog(self, make_client):
        client, session = make_client()
        with pytest.raises(BlogError, match="status"):
            client.set_status("p", "archived")
        assert session.calls == []

    @pytest.mark.unit
    def test_search_tags_and_info(self, make_client):
        client, session = make_client()
        client.search_posts("two words", status="published", limit=3)
        assert session.last["url"] == "http://blog.test/api/v1/search"
        assert session.last["params"] == {"q": "two words", "status": "published", "limit": 3}
        client.list_tags(status="draft")
        assert (session.last["url"], session.last["params"]) == ("http://blog.test/api/v1/tags", {"status": "draft"})


class TestDelete:
    @pytest.mark.unit
    def test_deleted(self, make_client):
        client, session = make_client(lambda m, u, k: make_response(200, {"slug": "p", "deleted": True}))
        assert client.delete_post("p") is True
        assert session.last["method"] == "DELETE"

    @pytest.mark.unit
    def test_already_gone_is_false_not_an_error(self, make_client):
        client, _ = make_client(lambda m, u, k: make_response(404, {"error": "Post 'p' not found"}))
        assert client.delete_post("p") is False

    @pytest.mark.unit
    def test_other_failures_are_not_swallowed(self, make_client):
        client, _ = make_client(lambda m, u, k: make_response(500, {"error": "Internal error"}))
        with pytest.raises(BlogError, match="Internal error"):
            client.delete_post("p")

    @pytest.mark.unit
    def test_an_unreachable_blog_is_not_reported_as_already_deleted(self, make_client):
        client, _ = make_client(lambda m, u, k: requests.exceptions.ConnectionError("refused"))
        with pytest.raises(BlogUnreachable):
            client.delete_post("p")


class TestUploadImage:
    @pytest.mark.unit
    def test_sends_the_file_as_multipart(self, make_client, tmp_path):
        picture = tmp_path / "pic.png"
        picture.write_bytes(b"\x89PNG fake")
        client, session = make_client(lambda m, u, k: make_response(201, {"url": "/media/x.png"}))
        assert client.upload_image(str(picture)) == {"url": "/media/x.png"}
        assert (session.last["method"], session.last["url"]) == ("POST", "http://blog.test/api/v1/media")
        assert session.last["files"]["file"][0] == "pic.png"

    @pytest.mark.unit
    def test_expands_the_home_directory(self, make_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / "p.png").write_bytes(b"x")
        client, session = make_client()
        client.upload_image("~/p.png")
        assert session.calls

    @pytest.mark.unit
    def test_missing_file(self, make_client):
        client, session = make_client()
        with pytest.raises(BlogError, match="No file at /no/such.png"):
            client.upload_image("/no/such.png")
        assert session.calls == []

    @pytest.mark.unit
    def test_a_directory_is_not_a_file(self, make_client, tmp_path):
        client, _ = make_client()
        with pytest.raises(BlogError, match="No file"):
            client.upload_image(str(tmp_path))

    @pytest.mark.unit
    def test_oversized_files_are_refused_before_uploading(self, make_client, tmp_path):
        big = tmp_path / "big.png"
        with big.open("wb") as handle:
            handle.truncate(9 * 1024 * 1024)
        client, session = make_client()
        with pytest.raises(BlogError, match="at most 8 MB"):
            client.upload_image(str(big))
        assert session.calls == []


class TestErrors:
    @pytest.mark.unit
    @pytest.mark.parametrize("status,payload,message", [
        (400, {"error": "title must not be empty"}, "title must not be empty"),
        (404, {"error": "Post 'x' not found"}, "Post 'x' not found"),
        (409, {"error": "Slug 'x' is already in use"}, "already in use"),
        (500, {"error": "Internal error"}, "Internal error"),
        (422, {"detail": "unexpected shape"}, "HTTP 422"),
        (503, [], "HTTP 503"),
    ])
    def test_blog_errors_carry_the_blogs_own_message(self, make_client, status, payload, message):
        client, _ = make_client(lambda m, u, k: make_response(status, payload))
        with pytest.raises(BlogError, match=message):
            client.get_post("x")

    @pytest.mark.unit
    def test_a_rejected_token_says_what_to_check(self, make_client):
        client, _ = make_client(lambda m, u, k: make_response(401, {"error": "Missing or invalid API token"}))
        with pytest.raises(BlogError, match="BLOG_API_TOKEN") as caught:
            client.info()
        assert not isinstance(caught.value, BlogUnreachable)

    @pytest.mark.unit
    @pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
    def test_redirects_are_reported_not_followed(self, make_client, status):
        client, _ = make_client(lambda m, u, k: make_response(status, text="", headers={"Location": "https://elsewhere.example/"}))
        with pytest.raises(BlogError, match="redirected"):
            client.info()

    @pytest.mark.unit
    @pytest.mark.parametrize("text", ["<html>nginx welcome</html>", "", "not json"])
    def test_a_non_json_answer_means_the_wrong_address(self, make_client, text):
        client, _ = make_client(lambda m, u, k: make_response(200, text=text))
        with pytest.raises(BlogError, match="Is BLOG_URL the blog"):
            client.info()

    @pytest.mark.unit
    def test_connection_failure_says_how_to_start_the_blog(self, make_client):
        client, _ = make_client(lambda m, u, k: requests.exceptions.ConnectionError("Connection refused"))
        with pytest.raises(BlogUnreachable, match=r"python blog_mcp/blog/blog\.py"):
            client.info()

    @pytest.mark.unit
    def test_timeout(self, make_client):
        client, _ = make_client(lambda m, u, k: requests.exceptions.ReadTimeout("slow"), timeout=3)
        with pytest.raises(BlogUnreachable, match="within 3 seconds"):
            client.info()

    @pytest.mark.unit
    def test_tls_failure_points_at_the_setting(self, make_client):
        client, _ = make_client(lambda m, u, k: requests.exceptions.SSLError("self signed certificate"))
        with pytest.raises(BlogUnreachable, match="BLOG_VERIFY_TLS=false"):
            client.info()

    @pytest.mark.unit
    def test_errors_never_echo_the_token(self, make_client):
        for result in (requests.exceptions.ConnectionError("Bearer test-token refused"), make_response(401, {"error": "x"}),
                       make_response(500, text="<html>Bearer test-token</html>")):
            client, _ = make_client(lambda m, u, k, r=result: r)
            with pytest.raises(BlogError) as caught:
                client.info()
            assert "test-token" not in str(caught.value)

    @pytest.mark.unit
    def test_errors_are_tool_errors_so_fastmcp_reports_them_cleanly(self):
        assert issubclass(BlogError, ToolError) and issubclass(BlogUnreachable, BlogError)
