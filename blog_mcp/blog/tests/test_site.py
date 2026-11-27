"""Tests for the blog's website, run against a real server: reading, login, the admin editor, uploads, and headers."""

import asyncio
import http.client
import re
from dataclasses import replace

import pytest
from starlette.exceptions import HTTPException

from blog_app.app import BodyLimit, safe_next
from tests.conftest import GIF, JPEG, PASSWORD, PNG, USERNAME, RunningBlog

READING_ROUTES = ["/", "/post/anything", "/tag/x", "/tags", "/search", "/search?q=a"]
ADMIN_GET_ROUTES = ["/admin", "/admin/new", "/admin/edit/anything"]
ADMIN_FORM_POSTS = ["/admin/new", "/admin/edit/{slug}", "/admin/delete/{slug}", "/admin/publish/{slug}", "/admin/unpublish/{slug}"]


def publish(site, title, body="", **kw):
    return site.store.create_post(title, body, publish=True, **kw)


class TestPrivateByDefault:
    @pytest.mark.integration
    @pytest.mark.parametrize("path", READING_ROUTES)
    def test_every_reading_page_sends_visitors_to_login(self, site, path):
        publish(site, "Visible only to me")
        response = site.browser().get(path)
        assert response.status == 303
        assert response.location.startswith("/login?next=")
        assert "Visible only to me" not in response.text

    @pytest.mark.integration
    def test_login_remembers_where_you_were_going(self, site):
        assert site.browser().get("/post/x").location == "/login?next=/post/x"

    @pytest.mark.integration
    @pytest.mark.parametrize("path", ["/healthz", "/login", "/static/blog.css", "/robots.txt"])
    def test_only_the_login_page_and_static_files_are_open(self, site, path):
        assert site.browser().get(path).status == 200

    @pytest.mark.integration
    def test_search_engines_are_told_to_stay_away(self, site):
        browser = site.browser()
        assert "Disallow: /\n" in browser.get("/robots.txt").text
        assert "noindex" in browser.get("/login").headers["x-robots-tag"]

    @pytest.mark.integration
    def test_logged_in_home_shows_published_posts_not_drafts(self, site, admin):
        publish(site, "Live post", "Opening paragraph here.", tags=["python"])
        site.store.create_post("Secret draft", "nope")
        page = admin.get("/").text
        assert "Live post" in page and "Opening paragraph here." in page and "#python" in page
        assert "Secret draft" not in page
        assert "Test Blog" in page and "Notes for testing" in page

    @pytest.mark.integration
    def test_empty_blog_says_so(self, admin):
        assert "No posts have been published yet." in admin.get("/").text

    @pytest.mark.integration
    def test_post_page_renders_markdown(self, site, admin):
        publish(site, "Rendered", "## Section\n\nSome **bold** text.", tags=["a"])
        page = admin.get("/post/rendered").text
        assert "<h2>Section</h2>" in page and "<strong>bold</strong>" in page
        assert "<title>Rendered · Test Blog</title>" in page
        assert "Edit this post" in page

    @pytest.mark.integration
    def test_draft_is_viewable_by_me_with_a_banner(self, site, admin):
        site.store.create_post("Wip", "half written")
        page = admin.get("/post/wip").text
        assert "This post is a draft" in page and "half written" in page

    @pytest.mark.integration
    def test_unknown_post_is_a_404_page(self, admin):
        response = admin.get("/post/ghost")
        assert response.status == 404 and "Not found" in response.text

    @pytest.mark.integration
    def test_tags_and_tag_pages_cover_published_posts_only(self, site, admin):
        publish(site, "Public one", tags=["python", "notes"])
        site.store.create_post("Draft one", tags=["wip"])
        tags = admin.get("/tags").text
        assert "#python" in tags and "#notes" in tags and "#wip" not in tags
        page = admin.get("/tag/python").text
        assert "Public one" in page and "Draft one" not in page

    @pytest.mark.integration
    def test_tag_with_special_characters(self, site, admin):
        publish(site, "C plus plus", tags=["c++"])
        assert 'href="/tag/c%2B%2B"' in admin.get("/tags").text
        assert "C plus plus" in admin.get("/tag/c%2B%2B").text

    @pytest.mark.integration
    def test_search_finds_posts_and_includes_drafts_for_me(self, site, admin):
        publish(site, "Tomato notes", "Tomatoes need sun.")
        site.store.create_post("Blight idea", "tomato blight someday")
        page = admin.get("/search?q=tomato").text
        assert "Tomato notes" in page and "Blight idea" in page and "Draft</span>" in page
        assert "No posts match" in admin.get("/search?q=zzzz").text
        assert "Type a word" in admin.get("/search").text

    @pytest.mark.integration
    def test_pagination(self, site, admin):
        for i in range(12):
            publish(site, f"Entry {i:02d}")
        first, second = admin.get("/").text, admin.get("/?page=2").text
        assert "Entry 11" in first and "Entry 02" in first and "Entry 01" not in first and "Older" in first
        assert "Entry 01" in second and "Entry 00" in second and "Entry 11" not in second and "Newer" in second

    @pytest.mark.integration
    @pytest.mark.parametrize("page", ["abc", "-3", "0", "", "99999999999999999999"])
    def test_bad_page_numbers_are_harmless(self, admin, page):
        assert admin.get(f"/?page={page}").status == 200

    @pytest.mark.integration
    def test_head_requests(self, site, admin):
        publish(site, "Headable")
        response = admin.request("HEAD", "/post/headable")
        assert response.status == 200 and response.body == b""

    @pytest.mark.integration
    def test_wrong_method_is_a_405_page(self, admin):
        response = admin.post("/", form={})
        assert response.status == 405 and "not allowed" in response.text


class TestPublicMode:
    @pytest.mark.integration
    def test_published_posts_are_readable_by_anyone(self, public_site):
        publish(public_site, "Open post", "hello world", tags=["t"])
        anon = public_site.browser()
        for path in ("/", "/post/open-post", "/tag/t", "/tags", "/search?q=hello"):
            response = anon.get(path)
            assert response.status == 200, path
            assert "Open post" in response.text or path == "/tags"

    @pytest.mark.integration
    def test_drafts_stay_private(self, public_site):
        public_site.store.create_post("Hidden draft", "secret words", tags=["wip"])
        anon = public_site.browser()
        assert anon.get("/post/hidden-draft").status == 404
        assert "Hidden draft" not in anon.get("/").text
        assert "Hidden draft" not in anon.get("/search?q=secret").text
        assert "#wip" not in anon.get("/tags").text
        assert "Hidden draft" not in anon.get("/tag/wip").text

    @pytest.mark.integration
    def test_the_draft_is_visible_to_me(self, public_site):
        public_site.store.create_post("Hidden draft", "secret words")
        assert public_site.admin().get("/post/hidden-draft").status == 200

    @pytest.mark.integration
    @pytest.mark.parametrize("path", ADMIN_GET_ROUTES)
    def test_admin_still_needs_login(self, public_site, path):
        assert public_site.browser().get(path).status == 303

    @pytest.mark.integration
    def test_api_still_needs_the_token(self, public_site):
        assert public_site.browser().api("GET", "/api/v1/info", token=None).status == 401

    @pytest.mark.integration
    def test_pages_may_be_indexed_but_the_admin_is_disallowed(self, public_site):
        anon = public_site.browser()
        assert "x-robots-tag" not in anon.get("/").headers
        assert "noindex" not in anon.get("/").text
        robots = anon.get("/robots.txt").text
        assert "Disallow: /admin" in robots and "Disallow: /\n" not in robots

    @pytest.mark.integration
    def test_anonymous_visitors_see_a_login_link_not_admin_links(self, public_site):
        page = public_site.browser().get("/").text
        assert 'href="/login"' in page and "/admin" not in page


class TestTrustedHosts:
    @pytest.mark.integration
    def test_untrusted_host_header_is_rejected(self, public_site):
        response = public_site.browser().get("/", headers={"Host": "attacker.example"})
        assert response.status == 400 and "Invalid host header" in response.text

    @pytest.mark.integration
    def test_allowlisted_host_and_configured_public_origin(self, make_site):
        site = make_site(public=True, allowed_hosts=["127.0.0.1", "blog.example.test"],
                         public_url="https://blog.example.test")
        response = site.browser().api("GET", "/api/v1/info", headers={"Host": "blog.example.test"})
        assert response.status == 200
        assert response.json()["url"] == "https://blog.example.test"


class TestLogin:
    @pytest.mark.integration
    def test_login_page(self, site):
        page = site.browser().get("/login").text
        assert 'name="username"' in page and 'type="password"' in page and 'autocomplete="current-password"' in page

    @pytest.mark.integration
    def test_wrong_password_keeps_the_username_and_says_why(self, site):
        response = site.browser().post("/login", form={"username": USERNAME, "password": "nope", "next": "/"})
        assert response.status == 401
        assert "Wrong username or password." in response.text
        assert f'value="{USERNAME}"' in response.text
        assert not response.set_cookies()

    @pytest.mark.integration
    def test_wrong_username_is_rejected(self, site):
        assert site.browser().post("/login", form={"username": "intruder", "password": PASSWORD}).status == 401

    @pytest.mark.integration
    @pytest.mark.parametrize("form", [{}, {"username": USERNAME}, {"password": PASSWORD}, {"username": "", "password": ""}])
    def test_missing_fields_are_rejected(self, site, form):
        assert site.browser().post("/login", form=form).status == 401

    @pytest.mark.integration
    def test_success_sets_a_hardened_session_cookie_and_redirects(self, site):
        browser = site.browser()
        response = browser.post("/login", form={"username": USERNAME, "password": PASSWORD, "next": "/tags"})
        assert response.status == 303 and response.location == "/tags"
        cookie = response.set_cookies()[0]
        assert cookie.startswith("blog_session=")
        assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie and "Max-Age=1209600" in cookie
        assert "Secure" not in cookie  # plain HTTP: a Secure cookie would never be sent back
        assert browser.get("/admin").status == 200

    @pytest.mark.integration
    def test_cookie_is_secure_behind_an_https_proxy(self, site):
        response = site.browser().post("/login", form={"username": USERNAME, "password": PASSWORD},
                                       headers={"X-Forwarded-Proto": "https"})
        assert "Secure" in response.set_cookies()[0]
        assert response.headers["strict-transport-security"] == "max-age=31536000"

    @pytest.mark.integration
    @pytest.mark.parametrize("target", [
        "//evil.example", "https://evil.example", "/\\evil.example", "javascript:alert(1)", "", "evil", "/ok\nSet-Cookie: x=1",
    ])
    def test_login_never_redirects_off_site(self, site, target):
        response = site.browser().post("/login", form={"username": USERNAME, "password": PASSWORD, "next": target})
        assert response.status == 303 and response.location == "/admin"

    @pytest.mark.integration
    def test_logged_in_visitors_skip_the_login_page(self, admin):
        assert admin.get("/login?next=/tags").location == "/tags"

    @pytest.mark.unit
    @pytest.mark.parametrize("value,expected", [
        ("/tags", "/tags"), ("/post/a?x=1", "/post/a?x=1"), ("//x", "/admin"), ("http://x", "/admin"),
        ("/\\x", "/admin"), (None, "/admin"), ("", "/admin"), ("/a\r\nb", "/admin"),
    ])
    def test_safe_next(self, value, expected):
        assert safe_next(value) == expected

    @pytest.mark.integration
    def test_repeated_failures_lock_the_client_out_even_with_the_right_password(self, site):
        browser = site.browser()
        for _ in range(5):
            assert browser.post("/login", form={"username": USERNAME, "password": "wrong"}).status == 401
        locked = browser.post("/login", form={"username": USERNAME, "password": PASSWORD})
        assert locked.status == 429
        assert int(locked.headers["retry-after"]) > 0
        assert "Too many failed attempts" in locked.text
        assert not locked.set_cookies()
        assert browser.get("/admin").status == 303

    @pytest.mark.integration
    def test_a_good_login_resets_the_failure_count(self, site):
        browser = site.browser()
        for _ in range(4):
            browser.post("/login", form={"username": USERNAME, "password": "wrong"})
        assert browser.post("/login", form={"username": USERNAME, "password": PASSWORD}).status == 303
        site.blog.throttle.reset("127.0.0.1")
        for _ in range(4):
            assert site.browser().post("/login", form={"username": USERNAME, "password": "wrong"}).status == 401

    @pytest.mark.integration
    def test_a_forged_cookie_is_not_a_login(self, site):
        browser = site.browser()
        browser.cookies["blog_session"] = "eyJ1Ijoib3duZXIifQ.forged"
        assert browser.get("/admin").status == 303

    @pytest.mark.integration
    def test_logout_requires_the_csrf_token(self, site, admin):
        assert admin.post("/logout", form={}).status == 403
        assert admin.get("/admin").status == 200  # still logged in
        assert admin.post("/logout", form={"csrf": "wrong"}).status == 403
        copied_cookie = admin.cookies["blog_session"]
        response = admin.post("/logout", form={"csrf": admin.csrf()})
        assert response.status == 303 and response.location == "/login"
        assert admin.get("/admin").status == 303
        replay = site.browser()
        replay.cookies["blog_session"] = copied_cookie
        assert replay.get("/admin").status == 303

    @pytest.mark.integration
    def test_a_session_survives_a_server_restart_but_not_a_password_change(self, make_site):
        first = make_site()
        cookie = first.admin().cookies["blog_session"]
        first.stop()
        for password, still_logged_in in ((PASSWORD, True), ("a different password", False)):
            restarted = RunningBlog(replace(first.settings, password=password))
            try:
                browser = restarted.browser()
                browser.cookies["blog_session"] = cookie
                assert (browser.get("/admin").status == 200) is still_logged_in, password
            finally:
                restarted.stop()


class TestAdminAccess:
    @pytest.mark.integration
    @pytest.mark.parametrize("path", ADMIN_GET_ROUTES)
    def test_admin_pages_need_login(self, site, path):
        response = site.browser().get(path)
        assert response.status == 303 and response.location.startswith("/login?next=")

    @pytest.mark.integration
    @pytest.mark.parametrize("template", ADMIN_FORM_POSTS)
    def test_admin_actions_need_login(self, site, template):
        site.store.create_post("Target")
        response = site.browser().post(template.format(slug="target"), form={"title": "x"})
        assert response.status == 303 and response.location.startswith("/login")
        assert site.store.get_post("target")["title"] == "Target"
        assert site.store.get_post("target")["status"] == "draft"

    @pytest.mark.integration
    @pytest.mark.parametrize("path", ["/admin/preview", "/admin/upload"])
    def test_background_endpoints_answer_401_json(self, site, path):
        response = site.browser().post(path, body=b"x")
        assert response.status == 401 and "logged out" in response.json()["error"]

    @pytest.mark.integration
    def test_the_api_token_does_not_open_the_admin(self, site):
        response = site.browser().get("/admin", headers={"Authorization": "Bearer test-api-token-0123456789abcdef"})
        assert response.status == 303

    @pytest.mark.integration
    def test_state_cannot_be_changed_with_get(self, site, admin):
        site.store.create_post("Target")
        for path in ("/admin/publish/target", "/admin/delete/target", "/admin/unpublish/target"):
            assert admin.get(path).status == 405
        assert site.store.get_post("target")["status"] == "draft"


class TestCsrf:
    @pytest.fixture
    def target(self, site):
        return site.store.create_post("Target", "body", publish=True)

    @pytest.mark.integration
    @pytest.mark.parametrize("csrf", [None, "", "wrong", "x" * 200])
    @pytest.mark.parametrize("template", ADMIN_FORM_POSTS)
    def test_every_admin_form_refuses_a_missing_or_wrong_token(self, site, admin, target, template, csrf):
        form = {"title": "Hijacked", "body": "hijacked", "action": "unpublish"}
        if csrf is not None:
            form["csrf"] = csrf
        response = admin.post(template.format(slug="target"), form=form)
        assert response.status == 403 and "no longer valid" in response.text
        post = site.store.get_post("target")
        assert (post["title"], post["body"], post["status"]) == ("Target", "body", "published")
        assert site.store.stats()["total"] == 1

    @pytest.mark.integration
    def test_a_token_from_another_session_is_refused(self, site, admin, target):
        other = site.admin()
        response = admin.post("/admin/delete/target", form={"csrf": other.csrf()})
        assert response.status == 403
        assert site.store.get_post("target")

    @pytest.mark.integration
    @pytest.mark.parametrize("path", ["/admin/preview", "/admin/upload"])
    def test_background_endpoints_need_the_token_header(self, admin, path):
        assert admin.post(path, body=b"x").status == 403
        assert admin.post(path, body=b"x", headers={"X-CSRF-Token": "wrong"}).status == 403

    @pytest.mark.integration
    def test_the_token_in_the_form_works(self, site, admin, target):
        assert admin.post("/admin/delete/target", form={"csrf": admin.csrf()}).status == 303
        assert site.store.stats()["total"] == 0


class TestEditor:
    @pytest.mark.integration
    def test_editor_page(self, admin):
        page = admin.get("/admin/new").text
        for fragment in ('name="title"', 'name="slug"', 'name="tags"', 'name="summary"', 'id="body"', 'id="preview"',
                         'id="image-file"', 'value="save"', 'value="publish"', 'name="csrf"', "/static/admin.js"):
            assert fragment in page

    @pytest.mark.integration
    def test_save_draft(self, site, admin):
        response = admin.post("/admin/new", form={"csrf": admin.csrf(), "title": "My Post", "body": "Hello", "tags": "Python, #notes",
                                                  "action": "save"})
        assert response.status == 303 and response.location == "/admin/edit/my-post?msg=created"
        post = site.store.get_post("my-post")
        assert (post["status"], post["tags"], post["body"]) == ("draft", ["notes", "python"], "Hello")

    @pytest.mark.integration
    def test_publish_straight_away(self, site, admin):
        response = admin.post("/admin/new", form={"csrf": admin.csrf(), "title": "Live", "body": "x", "action": "publish"})
        assert response.location == "/admin/edit/live?msg=published"
        assert site.store.get_post("live")["status"] == "published"

    @pytest.mark.integration
    def test_custom_slug_and_summary(self, site, admin):
        admin.post("/admin/new", form={"csrf": admin.csrf(), "title": "T", "slug": "Custom Slug", "summary": "Short", "action": "save"})
        post = site.store.get_post("custom-slug")
        assert post["custom_summary"] == "Short"

    @pytest.mark.integration
    def test_browser_newlines_are_normalized(self, site, admin):
        admin.post("/admin/new", form={"csrf": admin.csrf(), "title": "T", "body": "a\r\nb\r\nc", "action": "save"})
        assert site.store.get_post("t")["body"] == "a\nb\nc"

    @pytest.mark.integration
    def test_validation_errors_keep_everything_you_typed(self, site, admin):
        form = {"csrf": admin.csrf(), "title": "", "body": "Hours of writing", "tags": "keep", "action": "save"}
        response = admin.post("/admin/new", form=form)
        assert response.status == 400
        assert "title must not be empty" in response.text and "Hours of writing" in response.text and 'value="keep"' in response.text
        assert site.store.stats()["total"] == 0

    @pytest.mark.integration
    def test_duplicate_slug_is_a_409_with_text_kept(self, site, admin):
        site.store.create_post("Taken", slug="taken")
        form = {"csrf": admin.csrf(), "title": "Other", "slug": "taken", "body": "my text", "action": "save"}
        response = admin.post("/admin/new", form=form)
        assert response.status == 409 and "already in use" in response.text and "my text" in response.text

    @pytest.mark.integration
    def test_editing_loads_the_post(self, site, admin):
        site.store.create_post("Original", "the body", tags=["a", "b"], summary="the summary")
        page = admin.get("/admin/edit/original").text
        assert 'value="Original"' in page and "the body" in page and 'value="a, b"' in page and "the summary" in page
        assert 'name="version" value="1"' in page

    @pytest.mark.integration
    def test_the_summary_field_shows_only_what_the_author_wrote(self, site, admin):
        site.store.create_post("Auto", "Derived opening paragraph.")
        page = admin.get("/admin/edit/auto").text
        assert re.search(r'name="summary"[^>]*></textarea>', page)  # empty: the excerpt is not copied into it

    @pytest.mark.integration
    def test_saving_changes(self, site, admin):
        site.store.create_post("Old", "old body", tags=["x"])
        csrf = admin.csrf("/admin/edit/old")
        response = admin.post("/admin/edit/old", form={"csrf": csrf, "version": "1", "title": "New", "slug": "old", "tags": "y, z",
                                                       "summary": "", "body": "new body", "action": "save"})
        assert response.status == 303 and response.location == "/admin/edit/old?msg=saved"
        post = site.store.get_post("old")
        assert (post["title"], post["body"], post["tags"], post["version"]) == ("New", "new body", ["y", "z"], 2)

    @pytest.mark.integration
    def test_renaming_the_slug(self, site, admin):
        site.store.create_post("Old")
        csrf = admin.csrf("/admin/edit/old")
        response = admin.post("/admin/edit/old", form={"csrf": csrf, "version": "1", "title": "Old", "slug": "brand-new", "action": "save"})
        assert response.location == "/admin/edit/brand-new?msg=saved"

    @pytest.mark.integration
    def test_publish_and_unpublish_from_the_editor(self, site, admin):
        site.store.create_post("T", "b")
        csrf = admin.csrf("/admin/edit/t")
        base = {"csrf": csrf, "title": "T", "slug": "t", "body": "b"}
        assert admin.post("/admin/edit/t", form={**base, "version": "1", "action": "publish"}).location.endswith("msg=published")
        assert site.store.get_post("t")["status"] == "published"
        version = site.store.get_post("t")["version"]
        unpublished = admin.post("/admin/edit/t", form={**base, "version": str(version), "action": "unpublish"})
        assert unpublished.location.endswith("msg=unpublished")
        assert site.store.get_post("t")["status"] == "draft"

    @pytest.mark.integration
    def test_buttons_match_the_post_state(self, site, admin):
        site.store.create_post("D")
        assert 'value="publish"' in admin.get("/admin/edit/d").text
        site.store.set_status("d", "published")
        page = admin.get("/admin/edit/d").text
        assert 'value="unpublish"' in page and 'value="publish"' not in page

    @pytest.mark.integration
    def test_a_stale_save_is_refused_and_your_text_is_kept(self, site, admin):
        site.store.create_post("Shared", "start")
        csrf = admin.csrf("/admin/edit/shared")
        site.store.update_post("shared", body="changed by the MCP server")
        response = admin.post("/admin/edit/shared", form={"csrf": csrf, "version": "1", "title": "Shared", "slug": "shared",
                                                          "body": "my competing edit", "action": "save"})
        assert response.status == 409
        assert "changed by someone else" in response.text
        assert "my competing edit" in response.text
        assert 'name="version" value="2"' in response.text  # saving again is a deliberate overwrite
        assert site.store.get_post("shared")["body"] == "changed by the MCP server"
        again = admin.post("/admin/edit/shared", form={"csrf": csrf, "version": "2", "title": "Shared", "slug": "shared",
                                                       "body": "my competing edit", "action": "save"})
        assert again.status == 303
        assert site.store.get_post("shared")["body"] == "my competing edit"

    @pytest.mark.integration
    def test_editing_a_missing_post_is_a_404(self, admin):
        assert admin.get("/admin/edit/ghost").status == 404
        assert admin.post("/admin/edit/ghost", form={"csrf": admin.csrf(), "title": "x"}).status == 404

    @pytest.mark.integration
    def test_hostile_values_are_escaped_in_the_form(self, site, admin):
        site.store.create_post('"><script>alert(1)</script>', "</textarea><script>alert(2)</script>",
                               summary='"><img src=x onerror=alert(3)>')
        page = admin.get("/admin/edit/script-alert-1-script").text
        assert "<script>" not in page and "<img src=x" not in page and "</textarea><script>" not in page


class TestDashboard:
    @pytest.mark.integration
    def test_lists_everything_with_counts(self, site, admin):
        publish(site, "Live")
        site.store.create_post("Wip")
        page = admin.get("/admin").text
        assert "Live" in page and "Wip" in page
        assert re.search(r"All <span class=\"count\">2</span>", page) and "Drafts <span" in page

    @pytest.mark.integration
    def test_status_filter(self, site, admin):
        publish(site, "Live")
        site.store.create_post("Wip")
        drafts, published = admin.get("/admin?status=draft").text, admin.get("/admin?status=published").text
        assert "Wip" in drafts and "Live" not in drafts
        assert "Live" in published and "Wip" not in published
        assert admin.get("/admin?status=bogus").status == 200

    @pytest.mark.integration
    def test_pagination(self, site, admin):
        for i in range(30):
            site.store.create_post(f"Draft {i:02d}")
        assert "Older" in admin.get("/admin").text
        second = admin.get("/admin?page=2").text
        assert "Newer" in second and "Draft 00" in second and "Draft 29" not in second

    @pytest.mark.integration
    def test_empty_state_points_at_the_editor(self, admin):
        assert 'href="/admin/new"' in admin.get("/admin").text

    @pytest.mark.integration
    def test_publish_unpublish_delete_from_the_list(self, site, admin):
        site.store.create_post("T")
        csrf = admin.csrf("/admin")
        assert admin.post("/admin/publish/t", form={"csrf": csrf}).location == "/admin?msg=published"
        assert site.store.get_post("t")["status"] == "published"
        assert admin.post("/admin/unpublish/t", form={"csrf": csrf}).location == "/admin?msg=unpublished"
        assert site.store.get_post("t")["status"] == "draft"
        assert admin.post("/admin/delete/t", form={"csrf": csrf}).location == "/admin?msg=deleted"
        assert site.store.stats()["total"] == 0

    @pytest.mark.integration
    def test_delete_buttons_ask_for_confirmation(self, site, admin):
        site.store.create_post("T")
        assert 'data-confirm="Delete this post permanently?"' in admin.get("/admin").text

    @pytest.mark.integration
    @pytest.mark.parametrize("action", ["delete", "publish", "unpublish"])
    def test_actions_on_a_missing_post_are_a_404(self, admin, action):
        assert admin.post(f"/admin/{action}/ghost", form={"csrf": admin.csrf()}).status == 404

    @pytest.mark.integration
    def test_notices_only_come_from_a_fixed_list(self, admin):
        page = admin.get("/admin?msg=%3Cscript%3Ealert(1)%3C/script%3E").text
        assert "<script>alert" not in page and 'role="status"' not in page
        assert "Post deleted." in admin.get("/admin?msg=deleted").text


class TestPreview:
    @pytest.mark.integration
    def test_renders_markdown(self, admin):
        response = admin.post("/admin/preview", body="# Hi\n\n**bold**".encode(), headers={"X-CSRF-Token": admin.csrf()})
        assert response.status == 200 and "<h1>Hi</h1>" in response.text and "<strong>bold</strong>" in response.text

    @pytest.mark.integration
    def test_hostile_markdown_is_neutralized(self, admin):
        text = "<script>alert(1)</script>\n\n[x](javascript:alert(1))\n\n<img src=x onerror=alert(1)>"
        response = admin.post("/admin/preview", body=text.encode(), headers={"X-CSRF-Token": admin.csrf()})
        assert "<script>" not in response.text and 'href="javascript' not in response.text and "<img src=x" not in response.text

    @pytest.mark.integration
    def test_survives_invalid_utf8(self, admin):
        assert admin.post("/admin/preview", body=b"\xff\xfe broken", headers={"X-CSRF-Token": admin.csrf()}).status == 200

    @pytest.mark.integration
    def test_empty_preview(self, admin):
        assert admin.post("/admin/preview", body=b"", headers={"X-CSRF-Token": admin.csrf()}).body == b""


class TestUploadsAndMedia:
    @pytest.fixture
    def upload(self, admin):
        def send(content, name="pic.png", token=True):
            return admin.post("/admin/upload", files={"file": (name, content)}, headers={"X-CSRF-Token": admin.csrf()} if token else {})
        return send

    @pytest.mark.integration
    @pytest.mark.parametrize("content,kind,mime", [(PNG, "png", "image/png"), (JPEG, "jpg", "image/jpeg"), (GIF, "gif", "image/gif")])
    def test_an_uploaded_image_is_stored_and_served(self, admin, upload, content, kind, mime):
        response = upload(content)
        assert response.status == 201
        url = response.json()["url"]
        assert re.fullmatch(rf"/media/[0-9a-f]{{32}}\.{kind}", url)
        served = admin.get(url)
        assert served.status == 200 and served.body == content and served.headers["content-type"] == mime
        assert served.headers["x-content-type-options"] == "nosniff"
        assert "sandbox" in served.headers["content-security-policy"]

    @pytest.mark.integration
    @pytest.mark.parametrize("content,name", [
        (b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'/>", "x.svg"),
        (b"<html><script>alert(1)</script></html>", "x.png"),
        (b"%PDF-1.7 fake", "x.png"), (b"MZ\x90\x00 fake exe", "x.jpg"), (b"just text", "x.gif"),
    ])
    def test_only_real_images_are_accepted_whatever_they_are_called(self, site, upload, content, name):
        response = upload(content, name)
        assert response.status == 400 and "PNG, JPEG, GIF, and WebP" in response.json()["error"]
        assert not (site.blog.media_dir.exists() and any(site.blog.media_dir.iterdir()))

    @pytest.mark.integration
    def test_empty_file(self, upload):
        assert upload(b"").status == 400

    @pytest.mark.integration
    def test_missing_file_field(self, admin):
        response = admin.post("/admin/upload", files={"other": ("x.png", PNG)}, headers={"X-CSRF-Token": admin.csrf()})
        assert response.status == 400 and "named 'file'" in response.json()["error"]

    @pytest.mark.integration
    def test_upload_needs_the_csrf_token(self, upload):
        assert upload(PNG, token=False).status == 403

    @pytest.mark.integration
    def test_a_declared_oversize_body_is_refused_without_reading_it(self, site, admin):
        conn = http.client.HTTPConnection("127.0.0.1", site.port, timeout=10)
        conn.putrequest("POST", "/admin/upload")
        conn.putheader("Content-Length", str(50 * 1024 * 1024))
        conn.putheader("Cookie", f"blog_session={admin.cookies['blog_session']}")
        conn.endheaders()
        assert conn.getresponse().status == 413
        conn.close()

    @pytest.mark.integration
    def test_private_blog_hides_media_from_visitors(self, site, admin, upload):
        url = upload(PNG).json()["url"]
        assert site.browser().get(url).status == 404
        assert admin.get(url).status == 200

    @pytest.mark.integration
    def test_public_blog_serves_media_to_anyone_who_has_the_link(self, public_site):
        admin = public_site.admin()
        url = admin.post("/admin/upload", files={"file": ("a.png", PNG)}, headers={"X-CSRF-Token": admin.csrf()}).json()["url"]
        assert public_site.browser().get(url).status == 200

    @pytest.mark.integration
    @pytest.mark.parametrize("path", [
        "/media/..%2f..%2fblog.db", "/media/../blog.db", "/media/blog.db", "/media/secret_key", "/media/" + "a" * 32 + ".png",
        "/media/" + "a" * 32 + ".svg", "/media/%2e%2e%2fsecret_key", "/media/" + "0" * 32 + ".png/../../blog.db",
    ])
    def test_media_cannot_be_used_to_read_other_files(self, site, admin, path):
        response = admin.get(path)
        assert response.status in (404, 405) and b"SQLite" not in response.body


class TestHostileContent:
    @pytest.mark.integration
    def test_titles_tags_summaries_and_bodies_are_escaped_on_every_page(self, site, admin):
        site.store.create_post('<script>alert("t")</script>', "<iframe src=//evil></iframe>\n\n[x](javascript:alert(1))",
                               tags=["<img src=x>"], summary="<b>sum</b>", publish=True)
        slug = site.store.list_posts()["posts"][0]["slug"]
        for path in ("/", f"/post/{slug}", "/tags", "/search?q=iframe", "/tag/%3Cimg%20src%3Dx%3E", "/admin", f"/admin/edit/{slug}"):
            page = admin.get(path).text
            for bad in ('<script>alert', "<img src=x>", "<b>sum</b>", "<iframe", 'href="javascript'):
                assert bad not in page, (path, bad)

    @pytest.mark.integration
    def test_search_text_is_escaped(self, admin):
        page = admin.get("/search?q=%22%3E%3Cscript%3Ealert(1)%3C/script%3E").text
        assert "<script>alert(1)" not in page and "&lt;script&gt;" in page

    @pytest.mark.integration
    def test_sql_injection_in_urls_is_inert(self, site, admin):
        publish(site, "Survivor")
        assert admin.get("/post/x'%20OR%20'1'='1").status == 404
        assert admin.get("/tag/x'%20OR%20'1'='1").status == 200
        assert admin.get("/search?q=%27%3B%20DROP%20TABLE%20posts%3B--").status == 200
        assert site.store.stats()["total"] == 1

    @pytest.mark.integration
    def test_static_files_cannot_escape_their_folder(self, site):
        browser = site.browser()
        for path in ("/static/../store.py", "/static/%2e%2e/store.py", "/static/..%2fstore.py", "/static/../../blog.py"):
            assert browser.get(path).status == 404

    @pytest.mark.integration
    def test_internal_errors_do_not_leak_details(self, site, admin, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("secret path /home/me/blog.db")

        monkeypatch.setattr(site.store, "list_posts", boom)
        response = admin.get("/")
        assert response.status == 500 and "secret path" not in response.text and "Something went wrong" in response.text


class TestHeaders:
    @pytest.mark.integration
    def test_security_headers_on_pages(self, admin):
        headers = admin.get("/admin").headers
        csp = headers["content-security-policy"]
        assert "default-src 'none'" in csp and "script-src 'self'" in csp and "frame-ancestors 'none'" in csp
        assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
        assert headers["x-content-type-options"] == "nosniff" and headers["x-frame-options"] == "DENY"
        assert headers["referrer-policy"] == "no-referrer"
        assert "no-store" in headers["cache-control"] and "noindex" in headers["x-robots-tag"]

    @pytest.mark.integration
    def test_security_headers_on_errors_and_redirects(self, site):
        browser = site.browser()
        for path in ("/", "/does-not-exist", "/api/v1/info"):
            headers = browser.get(path).headers
            assert headers["x-content-type-options"] == "nosniff" and "content-security-policy" in headers, path

    @pytest.mark.integration
    def test_pages_use_no_inline_script_or_style(self, site, admin):
        publish(site, "P")
        for path in ("/", "/post/p", "/admin", "/admin/new", "/login", "/tags"):
            page = admin.get(path).text
            assert not re.search(r"<script(?![^>]*\bsrc=)", page), path
            assert "<style" not in page and " style=" not in page and " onclick=" not in page, path

    @pytest.mark.integration
    def test_static_files_are_served_and_cacheable(self, site):
        css = site.browser().get("/static/blog.css")
        js = site.browser().get("/static/admin.js")
        assert css.headers["content-type"].startswith("text/css") and "max-age" in css.headers["cache-control"]
        assert "javascript" in js.headers["content-type"]

    @pytest.mark.integration
    def test_editor_loads_its_script_only_on_editor_pages(self, site, admin):
        publish(site, "P")
        assert "/static/admin.js" in admin.get("/admin/new").text
        assert "/static/admin.js" not in admin.get("/post/p").text


class TestBodyLimit:
    @staticmethod
    def run(declared, chunks, limit=100):
        sent = []

        async def app(scope, receive, send):
            while True:
                message = await receive()
                if not message.get("more_body"):
                    break
            await send({"type": "http.response.start", "status": 200, "headers": []})

        async def go():
            queue = list(chunks)

            async def receive():
                body = queue.pop(0)
                return {"type": "http.request", "body": body, "more_body": bool(queue)}

            async def send(message):
                sent.append(message)

            headers = [(b"content-length", declared)] if declared is not None else []
            await BodyLimit(app, lambda path: limit)({"type": "http", "headers": headers, "path": "/"}, receive, send)

        asyncio.run(go())
        return sent

    @pytest.mark.unit
    def test_small_bodies_pass(self):
        assert self.run(b"10", [b"x" * 10])[0]["status"] == 200

    @pytest.mark.unit
    def test_a_declared_length_over_the_limit_is_refused_at_once(self):
        assert self.run(b"101", [b"x"])[0]["status"] == 413

    @pytest.mark.unit
    def test_a_garbage_content_length_is_refused(self):
        assert self.run(b"abc", [b"x"])[0]["status"] == 413

    @pytest.mark.unit
    def test_a_chunked_body_with_no_declared_length_is_cut_off(self):
        with pytest.raises(HTTPException) as caught:
            self.run(None, [b"x" * 60, b"x" * 60])
        assert caught.value.status_code == 413

    @pytest.mark.unit
    def test_a_lying_content_length_cannot_smuggle_more(self):
        with pytest.raises(HTTPException):
            self.run(b"5", [b"x" * 60, b"x" * 60])


class TestThePasswordNeverLeaks:
    @pytest.mark.integration
    def test_after_logging_in_and_using_the_blog_the_password_is_nowhere(self, site):
        needle = PASSWORD.encode()
        browser = site.browser()
        seen = [browser.post("/login", form={"username": USERNAME, "password": PASSWORD, "next": "/admin"})]
        seen.append(browser.post("/admin/new", form={"csrf": browser.csrf(), "title": "A post", "body": "text", "action": "publish"}))
        for path in ("/", "/admin", "/admin/new", "/admin/edit/a-post", "/post/a-post", "/tags", "/search?q=text", "/login"):
            seen.append(browser.get(path))
        seen.append(site.browser().api("GET", "/api/v1/info"))
        seen.append(site.browser().post("/login", form={"username": USERNAME, "password": "wrong guess"}))
        for response in seen:
            assert needle not in response.body and PASSWORD not in repr(response.raw_headers)
        on_disk = b"".join(p.read_bytes() for p in site.settings.data_dir.rglob("*") if p.is_file())
        assert needle not in on_disk

    @pytest.mark.integration
    def test_the_session_cookie_carries_no_password_or_hash(self, site):
        import base64
        import json

        browser = site.browser()
        browser.post("/login", form={"username": USERNAME, "password": PASSWORD})
        payload = browser.cookies["blog_session"].split(".")[0]
        decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode()
        assert PASSWORD not in decoded and "pbkdf2" not in decoded
        assert set(json.loads(decoded)) == {"u", "csrf", "exp", "v"}

    @pytest.mark.integration
    def test_a_failed_login_page_never_echoes_what_was_typed_as_the_password(self, site):
        response = site.browser().post("/login", form={"username": USERNAME, "password": "hunter2-typed-by-mistake"})
        assert response.status == 401 and "hunter2-typed-by-mistake" not in response.text
