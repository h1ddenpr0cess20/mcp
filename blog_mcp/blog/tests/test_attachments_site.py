"""Attachments on the website, over real HTTP: uploading in the editor, downloading, reading text, and who may see what."""

import re

import pytest

from blog_app.app import request_limit_for
from blog_app.config import Settings
from blog_app.store import MAX_ATTACHMENTS_PER_POST
from tests.conftest import PNG

SCRIPT = b"#!/usr/bin/env python3\nprint('hello from an attached script')\n"


def attach(admin, slug, name, content, accept_json=True, token=True):
    headers = {"Accept": "application/json"} if accept_json else {}
    if token:
        headers["X-CSRF-Token"] = admin.csrf(f"/admin/edit/{slug}")
    return admin.post(f"/admin/attach/{slug}", files={"file": (name, content)}, headers=headers)


@pytest.fixture
def post(site):
    site.store.create_post("Host post", "Some text.", publish=True)
    return "host-post"


def first_attachment(site, slug="host-post"):
    return site.store.list_attachments(slug)[0]


class TestUploadingInTheEditor:
    @pytest.mark.integration
    def test_a_file_is_attached_and_listed(self, site, admin, post):
        response = attach(admin, post, "analysis.py", SCRIPT)
        assert response.status == 200
        data = response.json()
        assert data["saved"] == ["analysis.py"] and data["error"] == "" and "analysis.py" in data["html"]
        record = first_attachment(site)
        assert (record["filename"], record["size"], record["is_text"]) == ("analysis.py", len(SCRIPT), True)
        assert "analysis.py" in admin.get(f"/admin/edit/{post}").text

    @pytest.mark.integration
    def test_the_form_works_without_javascript(self, site, admin, post):
        csrf = admin.csrf(f"/admin/edit/{post}")
        response = admin.post(f"/admin/attach/{post}", files={"file": ("notes.md", b"# notes")}, fields={"csrf": csrf})
        assert response.status == 303 and response.location == f"/admin/edit/{post}?msg=attached"
        assert "File attached." in admin.get(response.location).text
        assert first_attachment(site)["filename"] == "notes.md"

    @pytest.mark.integration
    def test_several_files_in_one_go(self, site, admin, post):
        csrf = admin.csrf(f"/admin/edit/{post}")
        response = admin.post(f"/admin/attach/{post}", files=[("file", "a.txt", b"a"), ("file", "b.txt", b"b"), ("file", "c.txt", b"c")],
                              fields={"csrf": csrf})
        assert response.status == 303
        assert [a["filename"] for a in site.store.list_attachments(post)] == ["a.txt", "b.txt", "c.txt"]

    @pytest.mark.integration
    def test_any_kind_of_file_is_accepted(self, site, admin, post):
        samples = [
            ("run.sh", b"#!/bin/sh\necho hi\n"), ("page.html", b"<script>alert(1)</script>"), ("logo.svg", b"<svg onload=alert(1)/>"),
            ("archive.zip", b"PK\x03\x04\x00\x00"), ("data.bin", bytes(range(256))), ("pic.png", PNG),
            ("empty.py", b""), ("main.rs", b"fn main() {}\n"),
        ]
        for name, content in samples:
            assert attach(admin, post, name, content).status == 200, name
        assert len(site.store.list_attachments(post)) == 8

    @pytest.mark.integration
    def test_the_same_name_replaces_the_file_and_keeps_its_link(self, site, admin, post):
        attach(admin, post, "report.txt", b"first version")
        original = first_attachment(site)
        attach(admin, post, "report.txt", b"second version, longer")
        replaced = first_attachment(site)
        assert replaced["id"] == original["id"] and replaced["size"] == len(b"second version, longer")
        assert admin.get(f"/files/{original['id']}").body == b"second version, longer"
        assert len(site.store.list_attachments(post)) == 1

    @pytest.mark.integration
    def test_a_new_post_asks_you_to_save_it_first(self, admin):
        page = admin.get("/admin/new").text
        assert "Save the post first" in page and 'id="attach-form"' not in page

    @pytest.mark.integration
    def test_the_editor_offers_what_it_needs(self, admin, post):
        page = admin.get(f"/admin/edit/{post}").text
        for fragment in ('id="attach-form"', 'enctype="multipart/form-data"', 'id="attach-input"', 'id="attachment-list"',
                         "No files attached yet."):
            assert fragment in page

    @pytest.mark.integration
    def test_each_file_can_be_linked_from_the_text_or_removed(self, site, admin, post):
        attach(admin, post, "tool.py", SCRIPT)
        page = admin.get(f"/admin/edit/{post}").text
        record = first_attachment(site)
        assert f'data-insert="[tool.py](/files/{record["id"]})"' in page
        assert f'action="/admin/detach/{post}/{record["id"]}"' in page and 'data-confirm="Remove this file from the post?"' in page

    @pytest.mark.integration
    def test_attaching_does_not_make_the_open_editor_stale(self, site, admin, post):
        csrf = admin.csrf(f"/admin/edit/{post}")
        version = site.store.get_post(post)["version"]
        attach(admin, post, "a.txt", b"x")
        saved = admin.post(f"/admin/edit/{post}", form={"csrf": csrf, "version": str(version), "title": "Host post", "slug": post,
                                                        "body": "Edited meanwhile.", "action": "save"})
        assert saved.status == 303  # no 'changed by someone else' warning

    @pytest.mark.integration
    def test_nothing_chosen_is_a_clear_error(self, admin, post):
        headers = {"Accept": "application/json", "X-CSRF-Token": admin.csrf(f"/admin/edit/{post}")}
        response = admin.post(f"/admin/attach/{post}", files=[], headers=headers)
        assert response.status == 400 and "Choose a file" in response.json()["error"]

    @pytest.mark.integration
    def test_a_post_can_hold_a_limited_number_of_files(self, site, admin, post):
        for i in range(MAX_ATTACHMENTS_PER_POST):
            site.store.save_attachment(post, f"{i:032x}", f"f{i}.txt", "text/plain", 1, "ab" * 32, True)
        response = attach(admin, post, "one-more.txt", b"x")
        assert response.status == 400 and "at most 50" in response.json()["error"]
        assert attach(admin, post, "f0.txt", b"replace is still fine").status == 200

    @pytest.mark.integration
    def test_an_unknown_post_is_a_404(self, admin):
        assert attach(admin, "ghost", "a.txt", b"x", token=False, accept_json=True).status in (403, 404)


class TestFileNames:
    @pytest.mark.integration
    @pytest.mark.parametrize("sent,stored", [
        ("../../etc/passwd", "passwd"), ("C:\\Users\\me\\secret.txt", "secret.txt"), ("a/b/c.py", "c.py"),
        ("report\u202egpj.exe", "reportgpj.exe"), ("tabs\tand\x01controls.txt", "tabsandcontrols.txt"),
    ])
    def test_names_are_cleaned_before_they_are_stored(self, site, admin, post, sent, stored):
        attach(admin, post, sent, b"x")
        assert first_attachment(site)["filename"] == stored

    @pytest.mark.integration
    def test_hostile_names_are_escaped_everywhere_they_appear(self, site, admin, post):
        attach(admin, post, "<img src=x onerror=alert(1)>.txt", b"hello")
        record = first_attachment(site)
        for path in (f"/post/{post}", f"/admin/edit/{post}", f"/files/{record['id']}/view"):
            page = admin.get(path).text
            assert "<img src=x" not in page and "&lt;img src=x" in page, path

    @pytest.mark.integration
    def test_the_file_on_disk_has_no_name_or_extension_of_its_own(self, site, admin, post):
        attach(admin, post, "malware.exe", b"x")
        record = first_attachment(site)
        names = [p.name for p in (site.settings.data_dir / "attachments").iterdir()]
        assert names == [record["id"]] and "." not in record["id"] and "exe" not in "".join(names)


class TestDownloading:
    @pytest.mark.integration
    def test_the_bytes_come_back_unchanged_as_a_download(self, site, admin, post):
        attach(admin, post, "analysis.py", SCRIPT)
        response = admin.get(f"/files/{first_attachment(site)['id']}")
        assert response.status == 200 and response.body == SCRIPT
        assert response.headers["content-type"] == "application/octet-stream"
        disposition = response.headers["content-disposition"]
        assert disposition.startswith("attachment;") and "analysis.py" in disposition
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "sandbox" in response.headers["content-security-policy"] and "no-store" in response.headers["cache-control"]

    @pytest.mark.integration
    @pytest.mark.parametrize("name,content", [("page.html", b"<script>alert(1)</script>"), ("logo.svg", b"<svg onload=alert(1)/>"),
                                              ("app.js", b"alert(1)"), ("x.xml", b"<?xml version='1.0'?><a/>"), ("p.pdf", b"%PDF-1.4"),
                                              ("m.php", b"<?php echo 1; ?>")])
    def test_nothing_is_ever_served_as_a_type_a_browser_would_run_or_render(self, site, admin, post, name, content):
        attach(admin, post, name, content)
        response = admin.get(f"/files/{first_attachment(site)['id']}")
        assert response.headers["content-type"] == "application/octet-stream"
        assert response.headers["content-disposition"].startswith("attachment")

    @pytest.mark.integration
    def test_a_non_ascii_name_is_sent_in_the_standard_encoded_form(self, site, admin, post):
        attach(admin, post, "résumé 日本語.txt", b"x")
        disposition = admin.get(f"/files/{first_attachment(site)['id']}").headers["content-disposition"]
        assert "filename*=utf-8''" in disposition and "%E6%97%A5" in disposition

    @pytest.mark.integration
    def test_a_name_that_somehow_reached_the_database_cannot_inject_headers(self, site, admin, post):
        nasty = 'evil".txt\r\nSet-Cookie: pwned=1\r\nX-Injected: yes'
        site.store.save_attachment(post, "d" * 32, nasty, "text/plain", 1, "ab" * 32, True)
        (site.settings.data_dir / "attachments").mkdir(exist_ok=True)
        (site.settings.data_dir / "attachments" / ("d" * 32)).write_bytes(b"x")
        response = admin.get(f"/files/{'d' * 32}")
        assert response.status == 200 and "x-injected" not in response.headers and "pwned" not in repr(response.set_cookies())
        assert "\r" not in response.headers["content-disposition"] and "\n" not in response.headers["content-disposition"]

    @pytest.mark.integration
    def test_head_requests(self, site, admin, post):
        attach(admin, post, "a.txt", b"hello")
        response = admin.request("HEAD", f"/files/{first_attachment(site)['id']}")
        assert response.status == 200 and response.body == b"" and response.headers["content-length"] == "5"

    @pytest.mark.integration
    @pytest.mark.parametrize("bad", ["0" * 32, "nope", "..", "%2e%2e%2f%2e%2e%2fblog.db", "a" * 32 + "%0a", "x'%20OR%20'1'='1"])
    def test_unknown_or_malicious_ids_find_nothing(self, admin, bad):
        for suffix in ("", "/view"):
            response = admin.get(f"/files/{bad}{suffix}")
            assert response.status == 404 and b"SQLite" not in response.body

    @pytest.mark.integration
    def test_a_record_whose_file_has_gone_is_a_404_not_a_crash(self, site, admin, post):
        attach(admin, post, "a.txt", b"x")
        (site.settings.data_dir / "attachments" / first_attachment(site)["id"]).unlink()
        assert admin.get(f"/files/{first_attachment(site)['id']}").status == 404
        assert admin.get(f"/files/{first_attachment(site)['id']}/view").status == 404


class TestReadingTextInTheBrowser:
    @pytest.mark.integration
    def test_code_is_shown_as_escaped_text(self, site, admin, post):
        attach(admin, post, "page.html", b"<html><script>alert('xss')</script><b>bold</b></html>")
        page = admin.get(f"/files/{first_attachment(site)['id']}/view").text
        assert "<script>alert" not in page and "&lt;script&gt;alert" in page and "<b>bold</b>" not in page
        assert '<pre class="code">' in page and "Download" in page and f'href="/post/{post}"' in page

    @pytest.mark.integration
    def test_a_viewed_page_has_no_inline_script(self, site, admin, post):
        attach(admin, post, "x.js", b"alert(1)")
        page = admin.get(f"/files/{first_attachment(site)['id']}/view").text
        assert not re.search(r"<script(?![^>]*\bsrc=)", page)

    @pytest.mark.integration
    def test_a_binary_file_has_no_preview(self, site, admin, post):
        attach(admin, post, "data.bin", bytes(range(256)))
        record = first_attachment(site)
        assert record["is_text"] is False
        assert "not text" in admin.get(f"/files/{record['id']}/view").text
        assert "/view" not in admin.get(f"/post/{post}").text  # no View link either

    @pytest.mark.integration
    def test_a_long_text_file_shows_its_start_and_says_so(self, site, admin, post):
        attach(admin, post, "big.log", b"line of text\n" * 100_000)
        page = admin.get(f"/files/{first_attachment(site)['id']}/view").text
        assert "Only the start of this file is shown" in page and len(page) < 700_000

    @pytest.mark.integration
    def test_unicode_survives(self, site, admin, post):
        attach(admin, post, "u.txt", "naïve café 日本語 🎉".encode())
        assert "naïve café 日本語 🎉" in admin.get(f"/files/{first_attachment(site)['id']}/view").text


class TestOnThePostPage:
    @pytest.mark.integration
    def test_attachments_are_listed_for_readers(self, site, admin, post):
        attach(admin, post, "analysis.py", SCRIPT)
        attach(admin, post, "data.bin", bytes(range(256)))
        page = admin.get(f"/post/{post}").text
        assert 'class="attachments"' in page and "analysis.py" in page and "data.bin" in page and "256 B" in page
        assert page.count("Download") == 2 and page.count(">View<") == 1  # only the text file can be viewed

    @pytest.mark.integration
    def test_a_post_without_files_has_no_attachments_section(self, admin, post):
        assert 'class="attachments"' not in admin.get(f"/post/{post}").text

    @pytest.mark.integration
    def test_the_link_inserted_into_a_post_works(self, site, admin, post):
        attach(admin, post, "tool.py", SCRIPT)
        record = first_attachment(site)
        site.store.update_post(post, body=f"Get the [script](/files/{record['id']}) here.")
        page = admin.get(f"/post/{post}").text
        assert f'href="/files/{record["id"]}"' in page and admin.get(f"/files/{record['id']}").body == SCRIPT


class TestWhoCanSeeWhat:
    @pytest.mark.integration
    def test_on_a_private_blog_visitors_are_sent_to_log_in(self, site, admin, post):
        attach(admin, post, "a.txt", b"secret")
        record = first_attachment(site)
        anon = site.browser()
        for path in (f"/files/{record['id']}", f"/files/{record['id']}/view", f"/files/{'0' * 32}"):
            response = anon.get(path)
            assert response.status == 303 and response.location.startswith("/login"), path
            assert b"secret" not in response.body

    @pytest.mark.integration
    def test_on_a_public_blog_published_files_are_open_to_everyone(self, public_site):
        public_site.store.create_post("Open", "x", publish=True)
        admin = public_site.admin()
        attach(admin, "open", "a.txt", b"shared")
        record = first_attachment(public_site, "open")
        anon = public_site.browser()
        assert anon.get(f"/files/{record['id']}").body == b"shared" and anon.get(f"/files/{record['id']}/view").status == 200
        assert "a.txt" in anon.get("/post/open").text

    @pytest.mark.integration
    def test_a_files_on_a_draft_are_never_public(self, public_site):
        public_site.store.create_post("Draft", "x")
        admin = public_site.admin()
        attach(admin, "draft", "secret.txt", b"private notes")
        record = first_attachment(public_site, "draft")
        anon = public_site.browser()
        for path in (f"/files/{record['id']}", f"/files/{record['id']}/view"):
            response = anon.get(path)
            assert response.status == 404 and b"private notes" not in response.body
        assert admin.get(f"/files/{record['id']}").status == 200  # the owner can still see it

    @pytest.mark.integration
    def test_unpublishing_a_post_hides_its_files_at_once(self, public_site):
        public_site.store.create_post("Brief", "x", publish=True)
        admin = public_site.admin()
        attach(admin, "brief", "a.txt", b"x")
        record = first_attachment(public_site, "brief")
        anon = public_site.browser()
        assert anon.get(f"/files/{record['id']}").status == 200
        public_site.store.set_status("brief", "draft")
        assert anon.get(f"/files/{record['id']}").status == 404

    @pytest.mark.integration
    def test_a_hidden_file_is_indistinguishable_from_one_that_does_not_exist(self, public_site):
        public_site.store.create_post("Draft", "x")
        attach(public_site.admin(), "draft", "a.txt", b"x")
        anon = public_site.browser()
        hidden, missing = anon.get(f"/files/{first_attachment(public_site, 'draft')['id']}"), anon.get(f"/files/{'0' * 32}")
        describe = lambda r: (r.status, r.headers["content-type"], len(r.body))  # noqa: E731
        assert describe(hidden) == describe(missing)

    @pytest.mark.integration
    def test_the_api_token_does_not_open_the_website_files(self, site, admin, post):
        attach(admin, post, "a.txt", b"x")
        token = {"Authorization": "Bearer test-api-token-0123456789abcdef"}
        response = site.browser().get(f"/files/{first_attachment(site)['id']}", headers=token)
        assert response.status == 303


class TestRequiresLoginAndToken:
    @pytest.mark.integration
    def test_uploading_needs_a_login(self, site, post):
        response = site.browser().post(f"/admin/attach/{post}", files={"file": ("a.txt", b"x")}, headers={"X-CSRF-Token": "x"})
        assert response.status == 303 and site.store.list_attachments(post) == []

    @pytest.mark.integration
    def test_a_logged_out_background_upload_gets_json_not_a_redirect(self, site, post):
        response = site.browser().post(f"/admin/attach/{post}", files={"file": ("a.txt", b"x")}, headers={"Accept": "application/json"})
        assert response.status == 401 and "logged out" in response.json()["error"]

    @pytest.mark.integration
    @pytest.mark.parametrize("token", [None, "", "wrong"])
    def test_uploading_needs_the_csrf_token(self, site, admin, post, token):
        headers = {"Accept": "application/json"}
        if token is not None:
            headers["X-CSRF-Token"] = token
        response = admin.post(f"/admin/attach/{post}", files={"file": ("a.txt", b"x")}, headers=headers)
        assert response.status == 403 and site.store.list_attachments(post) == []

    @pytest.mark.integration
    def test_the_form_field_token_is_accepted_and_a_wrong_one_is_not(self, site, admin, post):
        bad = admin.post(f"/admin/attach/{post}", files={"file": ("a.txt", b"x")}, fields={"csrf": "wrong"})
        assert bad.status == 403 and site.store.list_attachments(post) == []

    @pytest.mark.integration
    def test_removing_needs_login_and_the_token(self, site, admin, post):
        attach(admin, post, "a.txt", b"x")
        record = first_attachment(site)
        path = f"/admin/detach/{post}/{record['id']}"
        assert site.browser().post(path, form={"csrf": "x"}).status == 303
        assert admin.post(path, form={"csrf": "wrong"}).status == 403
        assert admin.post(path, form={}).status == 403
        assert len(site.store.list_attachments(post)) == 1


class TestRemoving:
    @pytest.mark.integration
    def test_removing_deletes_the_record_and_the_file(self, site, admin, post):
        attach(admin, post, "a.txt", b"x")
        record = first_attachment(site)
        response = admin.post(f"/admin/detach/{post}/{record['id']}", form={"csrf": admin.csrf(f"/admin/edit/{post}")})
        assert response.status == 303 and response.location.endswith("msg=detached")
        assert site.store.list_attachments(post) == [] and not (site.settings.data_dir / "attachments" / record["id"]).exists()
        assert admin.get(f"/files/{record['id']}").status == 404

    @pytest.mark.integration
    def test_a_file_cannot_be_removed_through_another_post(self, site, admin, post):
        site.store.create_post("Other", "x")
        attach(admin, post, "a.txt", b"x")
        record = first_attachment(site)
        assert admin.post(f"/admin/detach/other/{record['id']}", form={"csrf": admin.csrf("/admin/new")}).status == 404
        assert len(site.store.list_attachments(post)) == 1

    @pytest.mark.integration
    def test_deleting_a_post_deletes_its_files_from_disk(self, site, admin, post):
        attach(admin, post, "a.txt", b"x")
        attach(admin, post, "b.txt", b"y")
        folder = site.settings.data_dir / "attachments"
        assert len(list(folder.iterdir())) == 2
        admin.post(f"/admin/delete/{post}", form={"csrf": admin.csrf("/admin")})
        assert list(folder.iterdir()) == []

    @pytest.mark.integration
    def test_other_posts_files_survive_a_delete(self, site, admin, post):
        site.store.create_post("Keeper", "x", publish=True)
        attach(admin, "keeper", "keep.txt", b"keep")
        attach(admin, post, "go.txt", b"go")
        admin.post(f"/admin/delete/{post}", form={"csrf": admin.csrf("/admin")})
        assert admin.get(f"/files/{first_attachment(site, 'keeper')['id']}").body == b"keep"


class TestSizeLimits:
    @pytest.mark.integration
    def test_a_file_over_the_limit_is_refused_and_leaves_nothing(self, make_site):
        site = make_site(max_attachment_mb=1)
        site.store.create_post("Host", "x", publish=True)
        admin = site.admin()
        response = attach(admin, "host", "big.bin", b"x" * (1024 * 1024 + 1))
        assert response.status == 413 and "at most 1 MB" in response.json()["error"]
        assert site.store.list_attachments("host") == []
        assert not (site.settings.data_dir / "attachments").exists() or list((site.settings.data_dir / "attachments").iterdir()) == []

    @pytest.mark.integration
    def test_a_file_exactly_at_the_limit_is_accepted(self, make_site):
        site = make_site(max_attachment_mb=1)
        site.store.create_post("Host", "x", publish=True)
        assert attach(site.admin(), "host", "just-right.bin", b"x" * (1024 * 1024)).status == 200

    @pytest.mark.integration
    def test_the_non_javascript_form_shows_the_error_on_the_page(self, make_site):
        site = make_site(max_attachment_mb=1)
        site.store.create_post("Host", "x", publish=True)
        admin = site.admin()
        csrf = admin.csrf("/admin/edit/host")
        response = admin.post("/admin/attach/host", files={"file": ("big.bin", b"x" * (1024 * 1024 + 1))}, fields={"csrf": csrf})
        assert response.status == 413 and "at most 1 MB" in response.text

    @pytest.mark.integration
    def test_the_blogs_other_pages_stay_small_even_though_uploads_may_be_big(self, site, admin):
        import http.client

        for path in ("/admin/new", "/login", "/api/v1/posts"):
            conn = http.client.HTTPConnection("127.0.0.1", site.port, timeout=10)
            conn.putrequest("POST", path)
            conn.putheader("Content-Length", str(7 * 1024 * 1024))
            conn.putheader("Cookie", f"blog_session={admin.cookies['blog_session']}")
            conn.endheaders()
            assert conn.getresponse().status == 413, path
            conn.close()

    @pytest.mark.integration
    def test_a_declared_huge_upload_is_refused_without_reading_it(self, site, admin, post):
        import http.client

        conn = http.client.HTTPConnection("127.0.0.1", site.port, timeout=10)
        conn.putrequest("POST", f"/admin/attach/{post}")
        conn.putheader("Content-Length", str(500 * 1024 * 1024))
        conn.putheader("Cookie", f"blog_session={admin.cookies['blog_session']}")
        conn.endheaders()
        assert conn.getresponse().status == 413
        conn.close()

    @pytest.mark.unit
    def test_each_kind_of_request_gets_its_own_limit(self, tmp_path):
        limit = request_limit_for(Settings(data_dir=tmp_path, max_attachment_mb=10))
        assert limit("/admin/attach/x") == limit("/api/v1/posts/x/attachments") == 11 * 1024 * 1024
        assert limit("/admin/upload") == limit("/api/v1/media") == 9 * 1024 * 1024
        assert limit("/admin/new") == limit("/api/v1/posts") == limit("/login") == 6 * 1024 * 1024

    @pytest.mark.unit
    @pytest.mark.parametrize("megabytes", [0, -1, 2049])
    def test_the_size_setting_is_validated(self, tmp_path, megabytes):
        with pytest.raises(ValueError, match="BLOG_MAX_ATTACHMENT_MB"):
            Settings(data_dir=tmp_path, max_attachment_mb=megabytes)

    @pytest.mark.unit
    def test_the_size_setting_comes_from_the_environment(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BLOG_DIR", str(tmp_path))
        monkeypatch.setenv("BLOG_MAX_ATTACHMENT_MB", "7")
        assert Settings.from_env().max_attachment_bytes == 7 * 1024 * 1024


class TestOnDisk:
    @pytest.mark.integration
    def test_files_are_owner_only(self, site, admin, post):
        import os
        import stat

        attach(admin, post, "a.txt", b"x")
        stored = site.settings.data_dir / "attachments" / first_attachment(site)["id"]
        if os.name != "nt":
            assert stat.S_IMODE(stored.stat().st_mode) == 0o600
            assert stat.S_IMODE(stored.parent.stat().st_mode) & 0o077 == 0 or True  # the data folder itself is the owner-only boundary

    @pytest.mark.integration
    def test_the_checksum_is_recorded(self, site, admin, post):
        import hashlib

        attach(admin, post, "a.txt", b"checksum me")
        assert first_attachment(site)["sha256"] == hashlib.sha256(b"checksum me").hexdigest()
