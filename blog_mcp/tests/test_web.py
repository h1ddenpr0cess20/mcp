"""Tests for the password-protected blog viewer, over real local HTTP connections."""

import base64
import http.client
import os
import shutil
import stat
import subprocess

import pytest

from blog_client import BlogServer
from tests.conftest import PASSWORD, USERNAME, basic_auth, fetch

ALL_ROUTES = ["/", "/post/anything", "/drafts", "/tags", "/tag/x", "/search?q=a", "/search", "/does-not-exist", "/post/"]


@pytest.fixture
def populated(blog):
    blog.create_post(
        "Published One", "Opening paragraph of the first post.\n\n## Section\n\nMore text.",
        tags=["python", "notes"], publish=True,
    )
    blog.create_post("Secret Draft", "Not ready yet.", tags=["wip"])
    return blog


class TestAuthentication:
    @pytest.mark.integration
    @pytest.mark.parametrize("path", ALL_ROUTES)
    def test_every_route_requires_credentials(self, viewer, populated, path):
        status, headers, body = fetch(viewer, path, authed=False)
        assert status == 401
        assert headers["www-authenticate"].startswith("Basic ")
        assert "Published One" not in body

    @pytest.mark.integration
    def test_wrong_password_is_rejected(self, viewer):
        assert fetch(viewer, "/", headers=basic_auth(password="wrong"), authed=False)[0] == 401

    @pytest.mark.integration
    def test_wrong_username_is_rejected(self, viewer):
        assert fetch(viewer, "/", headers=basic_auth(user="intruder"), authed=False)[0] == 401

    @pytest.mark.integration
    def test_password_prefix_is_rejected(self, viewer):
        assert fetch(viewer, "/", headers=basic_auth(password=PASSWORD[:-1]), authed=False)[0] == 401
        assert fetch(viewer, "/", headers=basic_auth(password=PASSWORD + "x"), authed=False)[0] == 401

    @pytest.mark.integration
    @pytest.mark.parametrize("header", [
        "Basic",
        "Basic ",
        "Basic !!!not-base64!!!",
        "Basic " + base64.b64encode(b"no-colon-here").decode(),
        "Basic " + base64.b64encode(b"\xff\xfe:\xff").decode(),
        "Bearer " + PASSWORD,
        "owner:" + PASSWORD,
    ])
    def test_malformed_authorization_headers_are_rejected(self, viewer, header):
        assert fetch(viewer, "/", headers={"Authorization": header}, authed=False)[0] == 401

    @pytest.mark.integration
    def test_scheme_is_case_insensitive(self, viewer):
        token = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
        assert fetch(viewer, "/", headers={"Authorization": f"basic {token}"}, authed=False)[0] == 200

    @pytest.mark.integration
    def test_password_may_contain_a_colon(self, blog):
        server = BlogServer(blog, host="127.0.0.1", port=0, username="owner", password="pa:ss:word")
        server.AUTH_FAIL_DELAY = 0
        server.POLL_INTERVAL = 0.01
        server.start()
        try:
            assert fetch(server, "/", headers=basic_auth(password="pa:ss:word"), authed=False)[0] == 200
            assert fetch(server, "/", headers=basic_auth(password="pa"), authed=False)[0] == 401
        finally:
            server.stop()

    @pytest.mark.integration
    def test_correct_credentials_are_accepted(self, viewer):
        assert fetch(viewer, "/")[0] == 200

    @pytest.mark.unit
    def test_authorized_helper(self, viewer):
        good = basic_auth()["Authorization"]
        assert viewer.authorized(good) is True
        assert viewer.authorized(None) is False
        assert viewer.authorized("") is False


class TestPasswordConfiguration:
    @pytest.mark.unit
    def test_generates_and_persists_a_password_when_none_configured(self, blog, monkeypatch):
        monkeypatch.delenv("BLOG_PASSWORD", raising=False)
        first = BlogServer(blog, port=0)
        assert first.password_source == str(blog.data_dir / "viewer_password")
        assert len(first.password) >= 20
        assert (blog.data_dir / "viewer_password").read_text().strip() == first.password
        second = BlogServer(blog, port=0)
        assert second.password == first.password

    @pytest.mark.unit
    @pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
    def test_generated_password_file_is_owner_only(self, blog, monkeypatch):
        monkeypatch.delenv("BLOG_PASSWORD", raising=False)
        BlogServer(blog, port=0)
        assert stat.S_IMODE(os.stat(blog.data_dir / "viewer_password").st_mode) == 0o600

    @pytest.mark.unit
    def test_empty_password_file_is_regenerated(self, blog, monkeypatch):
        monkeypatch.delenv("BLOG_PASSWORD", raising=False)
        (blog.data_dir / "viewer_password").write_text("\n")
        assert BlogServer(blog, port=0).password

    @pytest.mark.unit
    def test_configured_password_is_used_and_never_written_to_disk(self, blog, monkeypatch):
        monkeypatch.setenv("BLOG_PASSWORD", "from-the-environment")
        server = BlogServer(blog, port=0)
        assert server.password == "from-the-environment"
        assert server.password_source == "BLOG_PASSWORD"
        assert not (blog.data_dir / "viewer_password").exists()

    @pytest.mark.unit
    def test_environment_defaults(self, blog, monkeypatch):
        monkeypatch.setenv("BLOG_USERNAME", "alice")
        monkeypatch.setenv("BLOG_TITLE", "Alice's Notes")
        monkeypatch.setenv("BLOG_DESCRIPTION", "Private thoughts")
        monkeypatch.setenv("BLOG_PORT", "12345")
        server = BlogServer(blog, password="x")
        assert (server.username, server.site["title"], server.site["description"], server.port) == (
            "alice", "Alice's Notes", "Private thoughts", 12345)

    @pytest.mark.unit
    def test_defaults_bind_loopback_on_documented_port(self, blog, monkeypatch):
        for name in ("BLOG_HOST", "BLOG_PORT", "BLOG_USERNAME", "BLOG_TITLE"):
            monkeypatch.delenv(name, raising=False)
        server = BlogServer(blog, password="x")
        assert (server.host, server.port, server.username, server.site["title"]) == ("127.0.0.1", 9411, "owner", "Private Blog")

    @pytest.mark.unit
    @pytest.mark.parametrize("username", ["", "a:b"])
    def test_invalid_usernames_are_rejected(self, blog, username):
        with pytest.raises(ValueError, match="BLOG_USERNAME"):
            BlogServer(blog, port=0, username=username, password="x")

    @pytest.mark.unit
    def test_tls_cert_and_key_must_be_given_together(self, blog):
        with pytest.raises(ValueError, match="together"):
            BlogServer(blog, port=0, password="x", tls_cert="cert.pem")
        with pytest.raises(ValueError, match="together"):
            BlogServer(blog, port=0, password="x", tls_key="key.pem")


class TestPages:
    @pytest.mark.integration
    def test_home_lists_published_posts_and_hides_drafts(self, viewer, populated):
        status, _, body = fetch(viewer, "/")
        assert status == 200
        assert "Published One" in body
        assert "Opening paragraph of the first post." in body
        assert "Secret Draft" not in body
        assert "Test Blog" in body
        assert "Notes for testing" in body

    @pytest.mark.integration
    def test_home_when_empty(self, viewer):
        assert "No posts have been published yet." in fetch(viewer, "/")[2]

    @pytest.mark.integration
    def test_drafts_page_lists_only_drafts(self, viewer, populated):
        body = fetch(viewer, "/drafts")[2]
        assert "Secret Draft" in body
        assert "Published One" not in body
        assert "Draft</span>" in body

    @pytest.mark.integration
    def test_post_page_renders_markdown(self, viewer, populated):
        status, _, body = fetch(viewer, "/post/published-one")
        assert status == 200
        assert "<h2>Section</h2>" in body
        assert "<title>Published One · Test Blog</title>" in body
        assert "#python" in body
        assert "This post is a draft" not in body

    @pytest.mark.integration
    def test_draft_post_is_viewable_with_a_banner(self, viewer, populated):
        status, _, body = fetch(viewer, "/post/secret-draft")
        assert status == 200
        assert "This post is a draft" in body

    @pytest.mark.integration
    def test_unpublishing_removes_a_post_from_home(self, viewer, populated):
        populated.set_status("published-one", "draft")
        assert "Published One" not in fetch(viewer, "/")[2]

    @pytest.mark.integration
    def test_unknown_post_is_404(self, viewer):
        status, _, body = fetch(viewer, "/post/ghost")
        assert status == 404
        assert "Not found" in body

    @pytest.mark.integration
    @pytest.mark.parametrize("path", ["/nope", "/post", "/post/a/b", "/tag", "/drafts/extra", "/tags/extra"])
    def test_unknown_paths_are_404(self, viewer, path):
        assert fetch(viewer, path)[0] == 404

    @pytest.mark.integration
    def test_tag_page_and_tags_index(self, viewer, populated):
        status, _, body = fetch(viewer, "/tag/python")
        assert status == 200
        assert "Published One" in body
        assert "Secret Draft" not in body
        tags = fetch(viewer, "/tags")[2]
        assert "#python" in tags and "#notes" in tags
        assert "#wip" not in tags  # tags only on drafts are not listed publicly

    @pytest.mark.integration
    def test_tag_with_special_characters_round_trips(self, viewer, blog):
        blog.create_post("C plus plus", tags=["c++"], publish=True)
        assert 'href="/tag/c%2B%2B"' in fetch(viewer, "/tags")[2]
        status, _, body = fetch(viewer, "/tag/c%2B%2B")
        assert status == 200
        assert "C plus plus" in body

    @pytest.mark.integration
    def test_search_covers_drafts_too(self, viewer, populated):
        body = fetch(viewer, "/search?q=ready")[2]
        assert "Secret Draft" in body
        assert "Published One" not in body

    @pytest.mark.integration
    def test_search_without_query_and_without_results(self, viewer, populated):
        assert "Type a word" in fetch(viewer, "/search")[2]
        assert "No posts match" in fetch(viewer, "/search?q=zzzz")[2]

    @pytest.mark.integration
    def test_pagination(self, viewer, blog, clock):
        for i in range(12):
            blog.create_post(f"Entry {i:02d}", publish=True)
            clock()
        page1 = fetch(viewer, "/")[2]
        page2 = fetch(viewer, "/?page=2")[2]
        assert "Entry 11" in page1 and "Entry 02" in page1 and "Entry 01" not in page1
        assert "Older" in page1 and "Newer" not in page1
        assert "Entry 01" in page2 and "Entry 00" in page2 and "Entry 11" not in page2
        assert "Newer" in page2 and "Older" not in page2

    @pytest.mark.integration
    @pytest.mark.parametrize("page", ["abc", "-3", "0", "", "99999999999999999999"])
    def test_bad_page_numbers_do_not_break_the_listing(self, viewer, populated, page):
        assert fetch(viewer, f"/?page={page}")[0] == 200


class TestHostileContent:
    @pytest.mark.integration
    def test_titles_tags_and_summaries_are_escaped_everywhere(self, viewer, blog):
        blog.create_post('<script>alert("t")</script>', "body", tags=["<img src=x>"], summary="<b>sum</b>", publish=True)
        slug = blog.list_posts()["posts"][0]["slug"]
        for path in ("/", f"/post/{slug}", "/tags", "/search?q=body", "/tag/%3Cimg%20src%3Dx%3E"):
            body = fetch(viewer, path)[2]
            assert "<script>alert" not in body, path
            assert "<img src=x>" not in body, path
            assert "<b>sum</b>" not in body, path

    @pytest.mark.integration
    def test_body_html_and_dangerous_links_are_neutralized(self, viewer, blog):
        blog.create_post("Evil", "<script>steal()</script>\n\n[x](javascript:steal())\n\n<iframe src='//evil'></iframe>", publish=True)
        body = fetch(viewer, "/post/evil")[2]
        assert "<script>steal" not in body
        assert "<iframe" not in body
        assert 'href="javascript' not in body

    @pytest.mark.integration
    def test_search_query_is_escaped_in_the_page(self, viewer):
        body = fetch(viewer, "/search?q=%22%3E%3Cscript%3Ealert(1)%3C/script%3E")[2]
        assert "<script>alert(1)" not in body
        assert "&lt;script&gt;" in body

    @pytest.mark.integration
    def test_path_traversal_attempts_find_nothing(self, viewer, populated):
        for path in ("/post/..%2f..%2fetc%2fpasswd", "/post/%2e%2e/%2e%2e/viewer_password", "/../viewer_password"):
            status, _, body = fetch(viewer, path)
            assert status == 404
            assert PASSWORD not in body

    @pytest.mark.integration
    def test_sql_injection_in_urls_is_inert(self, viewer, populated):
        assert fetch(viewer, "/post/x'%20OR%20'1'='1")[0] == 404
        assert fetch(viewer, "/tag/x'%20OR%20'1'='1")[0] == 200
        assert populated.stats()["total"] == 2

    @pytest.mark.integration
    def test_internal_errors_do_not_leak_details(self, viewer, monkeypatch, capsys):
        def boom(*args, **kwargs):
            raise RuntimeError("secret database path /home/me/blog.db")

        monkeypatch.setattr(viewer.client, "list_posts", boom)
        status, _, body = fetch(viewer, "/")
        assert status == 500
        assert "secret database path" not in body
        assert "Something went wrong" in body
        assert "secret database path" in capsys.readouterr().err


class TestResponseHeaders:
    @pytest.mark.integration
    def test_security_headers_on_pages(self, viewer, populated):
        _, headers, body = fetch(viewer, "/post/published-one")
        csp = headers["content-security-policy"]
        assert "default-src 'none'" in csp
        assert "script-src" not in csp and "'unsafe-eval'" not in csp
        assert "frame-ancestors 'none'" in csp
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["referrer-policy"] == "no-referrer"
        assert "noindex" in headers["x-robots-tag"]
        assert "no-store" in headers["cache-control"]
        assert headers["content-type"] == "text/html; charset=utf-8"
        assert 'name="robots" content="noindex' in body

    @pytest.mark.integration
    def test_security_headers_on_the_login_challenge(self, viewer):
        _, headers, _ = fetch(viewer, "/", authed=False)
        assert "no-store" in headers["cache-control"]
        assert headers["content-type"] == "text/plain; charset=utf-8"
        assert headers["content-type"].count("text") == 1

    @pytest.mark.integration
    def test_head_returns_headers_without_a_body(self, viewer, populated):
        status, headers, body = fetch(viewer, "/post/published-one", method="HEAD")
        assert status == 200
        assert body == ""
        assert int(headers["content-length"]) > 0

    @pytest.mark.integration
    @pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
    def test_viewer_is_read_only(self, viewer, populated, method):
        status, _, _ = fetch(viewer, "/post/published-one", method=method)
        assert status in (401, 405, 501)
        assert populated.get_post("published-one")["status"] == "published"
        assert populated.stats()["total"] == 2

    @pytest.mark.integration
    def test_unauthenticated_unsupported_method_does_not_modify_anything(self, viewer, populated):
        assert fetch(viewer, "/post/published-one", method="DELETE", authed=False)[0] in (401, 405, 501)
        assert populated.stats()["total"] == 2


class TestAddressesAndLifecycle:
    @pytest.mark.unit
    def test_urls(self, blog):
        server = BlogServer(blog, host="127.0.0.1", port=4000, password="x")
        assert server.base_url == "http://127.0.0.1:4000"
        assert server.post_url("my-post") == "http://127.0.0.1:4000/post/my-post"

    @pytest.mark.unit
    def test_wildcard_host_is_advertised_as_loopback(self, blog):
        assert BlogServer(blog, host="0.0.0.0", port=4000, password="x").base_url == "http://127.0.0.1:4000"

    @pytest.mark.unit
    def test_ipv6_host_is_bracketed(self, blog):
        assert BlogServer(blog, host="::1", port=4000, password="x").base_url == "http://[::1]:4000"

    @pytest.mark.unit
    def test_tls_changes_the_scheme(self, blog):
        assert BlogServer(blog, port=4000, password="x", tls_cert="c.pem", tls_key="k.pem").base_url.startswith("https://")

    @pytest.mark.integration
    def test_ephemeral_port_is_resolved_on_start(self, viewer):
        assert viewer.port != 0
        assert viewer.base_url.endswith(f":{viewer.port}")

    @pytest.mark.integration
    def test_stop_releases_the_port(self, blog):
        server = BlogServer(blog, host="127.0.0.1", port=0, password="x")
        server.POLL_INTERVAL = 0.01
        server.start()
        port = server.port
        server.stop()
        with pytest.raises(OSError):
            http.client.HTTPConnection("127.0.0.1", port, timeout=2).request("GET", "/")
        server.stop()  # stopping twice is harmless

    @pytest.mark.integration
    def test_port_conflict_raises(self, viewer, blog):
        clash = BlogServer(blog, host="127.0.0.1", port=viewer.port, password="x")
        with pytest.raises(OSError):
            clash.start()

    @pytest.mark.integration
    def test_non_loopback_without_tls_warns(self, blog, capsys):
        server = BlogServer(blog, host="0.0.0.0", port=0, password="x")
        server.POLL_INTERVAL = 0.01
        server.start()
        try:
            assert "without TLS" in capsys.readouterr().err
        finally:
            server.stop()

    @pytest.mark.integration
    def test_loopback_does_not_warn(self, viewer, capsys):
        assert "WARNING" not in capsys.readouterr().err


@pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl not available to make a test certificate")
class TestTLS:
    @pytest.fixture
    def tls_viewer(self, blog, tmp_path):
        cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(cert),
             "-days", "1", "-subj", "/CN=localhost"],
            check=True, capture_output=True,
        )
        server = BlogServer(blog, host="127.0.0.1", port=0, password=PASSWORD, tls_cert=str(cert), tls_key=str(key))
        server.AUTH_FAIL_DELAY = 0
        server.POLL_INTERVAL = 0.01
        server.start()
        yield server
        server.stop()

    @pytest.mark.integration
    def test_serves_https_with_auth(self, tls_viewer, populated):
        assert tls_viewer.base_url.startswith("https://")
        assert fetch(tls_viewer, "/", authed=False)[0] == 401
        status, _, body = fetch(tls_viewer, "/")
        assert status == 200
        assert "Published One" in body

    @pytest.mark.integration
    def test_plain_http_is_not_served(self, tls_viewer):
        conn = http.client.HTTPConnection("127.0.0.1", tls_viewer.port, timeout=3)
        with pytest.raises((OSError, http.client.HTTPException)):
            conn.request("GET", "/", headers=basic_auth())
            conn.getresponse().read()

    @pytest.mark.integration
    def test_stalled_handshake_does_not_block_other_clients(self, tls_viewer, populated):
        import socket

        stalled = socket.create_connection(("127.0.0.1", tls_viewer.port), timeout=3)  # connects, never speaks TLS
        try:
            assert fetch(tls_viewer, "/")[0] == 200
        finally:
            stalled.close()
