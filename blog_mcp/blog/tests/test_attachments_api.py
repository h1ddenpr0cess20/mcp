"""Attachments through the JSON API (what the MCP server uses), over real HTTP."""

import hashlib

import pytest

from tests.conftest import API_TOKEN, PNG

CODE = b"def total(values):\n    return sum(values)\n"


@pytest.fixture
def api(site):
    browser = site.browser()
    return lambda method, path, **kw: browser.api(method, path, **kw)


@pytest.fixture
def post(site):
    site.store.create_post("Host post", "Some text.", publish=True)
    return "host-post"


def upload(api, slug, name, content, **kw):
    return api("POST", f"/api/v1/posts/{slug}/attachments", files={"file": (name, content)}, **kw)


class TestAuthentication:
    @pytest.mark.integration
    @pytest.mark.parametrize("method,path", [
        ("GET", "/api/v1/posts/host-post/attachments"), ("POST", "/api/v1/posts/host-post/attachments"),
        ("DELETE", "/api/v1/posts/host-post/attachments/" + "0" * 32), ("GET", "/api/v1/attachments/" + "0" * 32),
        ("GET", "/api/v1/attachments/" + "0" * 32 + "/download"),
    ])
    def test_every_endpoint_needs_the_token(self, site, post, method, path):
        for token in (None, "wrong", API_TOKEN[:-1]):
            assert site.browser().api(method, path, token=token).status == 401

    @pytest.mark.integration
    def test_a_browser_login_is_not_an_api_credential(self, site, post):
        site.store.save_attachment(post, "a" * 32, "a.txt", "text/plain", 1, "ab" * 32, True)
        admin = site.admin()
        assert admin.get(f"/api/v1/posts/{post}/attachments").status == 401
        assert admin.get("/api/v1/attachments/" + "a" * 32).status == 401

    @pytest.mark.integration
    def test_nothing_is_stored_without_the_token(self, site, post):
        response = site.browser().request("POST", f"/api/v1/posts/{post}/attachments", files={"file": ("a.txt", b"x")})
        assert response.status == 401 and site.store.list_attachments(post) == []


class TestUploading:
    @pytest.mark.integration
    def test_a_new_file(self, site, api, post):
        response = upload(api, post, "helpers.py", CODE)
        assert response.status == 201
        data = response.json()
        assert (data["filename"], data["size"], data["is_text"], data["replaced"]) == ("helpers.py", len(CODE), True, False)
        assert data["content_type"] == "text/x-python" and data["sha256"] == hashlib.sha256(CODE).hexdigest()
        assert data["url"] == f"{site.url}/files/{data['id']}" and data["view_url"] == data["url"] + "/view"
        assert site.blog.attachments.path(data["id"]).read_bytes() == CODE

    @pytest.mark.integration
    def test_the_same_name_replaces_it_and_keeps_the_same_id(self, api, post):
        first = upload(api, post, "notes.md", b"v1").json()
        second = upload(api, post, "notes.md", b"version two")
        assert second.status == 200 and second.json()["id"] == first["id"] and second.json()["replaced"] is True
        assert second.json()["size"] == 11
        assert api("GET", f"/api/v1/posts/{post}/attachments").json()["count"] == 1

    @pytest.mark.integration
    def test_binary_files_have_no_view_link(self, api, post):
        data = upload(api, post, "pic.png", PNG).json()
        assert data["is_text"] is False and "view_url" not in data

    @pytest.mark.integration
    def test_an_empty_file_is_fine(self, api, post):  # an empty __init__.py is a normal thing to attach
        data = upload(api, post, "__init__.py", b"").json()
        assert data["size"] == 0 and data["is_text"] is True

    @pytest.mark.integration
    def test_names_are_cleaned(self, api, post):
        assert upload(api, post, "../../etc/passwd", b"x").json()["filename"] == "passwd"

    @pytest.mark.integration
    def test_unicode_content_and_names(self, api, post):
        data = upload(api, post, "日本語.txt", "こんにちは 🎉".encode()).json()
        assert data["filename"] == "日本語.txt"
        assert api("GET", f"/api/v1/attachments/{data['id']}").json()["content"] == "こんにちは 🎉"

    @pytest.mark.integration
    @pytest.mark.parametrize("files", [{"other": ("a.txt", b"x")}, {}])
    def test_the_file_must_be_in_a_field_named_file(self, site, api, post, files):
        response = api("POST", f"/api/v1/posts/{post}/attachments", files=files)
        assert response.status == 400 and "field named 'file'" in response.json()["error"]
        assert site.store.list_attachments(post) == []

    @pytest.mark.integration
    def test_a_json_body_is_not_an_upload(self, api, post):
        response = api("POST", f"/api/v1/posts/{post}/attachments", json_body={"file": "x"})
        assert response.status == 400

    @pytest.mark.integration
    def test_an_unknown_post_is_a_404_and_stores_nothing(self, site, api):
        response = upload(api, "ghost", "a.txt", b"x")
        assert response.status == 404
        assert not (site.settings.data_dir / "attachments").exists() or list((site.settings.data_dir / "attachments").iterdir()) == []

    @pytest.mark.integration
    def test_too_large_is_a_413_and_leaves_nothing(self, make_site):
        site = make_site(max_attachment_mb=1)
        site.store.create_post("Host", "x", publish=True)
        api = site.browser().api
        response = upload(api, "host", "big.bin", b"x" * (1024 * 1024 + 1))
        assert response.status == 413 and "at most 1 MB" in response.json()["error"]
        assert site.store.list_attachments("host") == [] and list((site.settings.data_dir / "attachments").iterdir()) == []
        assert upload(api, "host", "fits.bin", b"x" * (1024 * 1024)).status == 201

    @pytest.mark.integration
    def test_a_post_holds_at_most_fifty_files(self, site, api, post):
        for i in range(50):
            site.store.save_attachment(post, f"{i:032x}", f"f{i}.txt", "text/plain", 1, "ab" * 32, True)
        response = upload(api, post, "extra.txt", b"x")
        assert response.status == 400 and "at most 50 attachments" in response.json()["error"]
        assert upload(api, post, "f1.txt", b"replacing is allowed").status == 200


class TestListingAndReading:
    @pytest.mark.integration
    def test_list(self, api, post):
        upload(api, post, "b.py", CODE)
        upload(api, post, "A.csv", b"a,b\n1,2\n")
        listing = api("GET", f"/api/v1/posts/{post}/attachments").json()
        assert listing["count"] == 2 and [a["filename"] for a in listing["attachments"]] == ["A.csv", "b.py"]
        assert all(a["url"].startswith("http") for a in listing["attachments"])

    @pytest.mark.integration
    def test_list_for_an_unknown_post(self, api):
        assert api("GET", "/api/v1/posts/ghost/attachments").status == 404

    @pytest.mark.integration
    def test_reading_a_text_file_returns_its_content(self, api, post):
        data = upload(api, post, "helpers.py", CODE).json()
        read = api("GET", f"/api/v1/attachments/{data['id']}").json()
        assert read["content"] == CODE.decode() and read["truncated"] is False
        assert (read["filename"], read["post_slug"], read["size"]) == ("helpers.py", post, len(CODE))

    @pytest.mark.integration
    def test_a_long_file_is_cut_short_on_request(self, api, post):
        data = upload(api, post, "long.txt", b"0123456789" * 100).json()
        read = api("GET", f"/api/v1/attachments/{data['id']}?max_bytes=25").json()
        assert read["content"] == "0123456789" * 2 + "01234" and read["truncated"] is True

    @pytest.mark.integration
    def test_the_default_is_generous_for_source_code(self, api, post):
        data = upload(api, post, "module.py", b"x = 1\n" * 40_000).json()  # about 240 KB
        assert api("GET", f"/api/v1/attachments/{data['id']}").json()["truncated"] is False

    @pytest.mark.integration
    def test_a_binary_file_returns_details_but_no_content(self, api, post):
        data = upload(api, post, "pic.png", PNG).json()
        read = api("GET", f"/api/v1/attachments/{data['id']}").json()
        assert read["content"] is None and read["is_text"] is False and read["size"] == len(PNG)

    @pytest.mark.integration
    @pytest.mark.parametrize("query,status", [("max_bytes=abc", 400), ("max_bytes=", 400), ("max_bytes=0", 200), ("max_bytes=-5", 200),
                                              ("max_bytes=99999999999", 200)])
    def test_max_bytes_is_validated_and_clamped(self, api, post, query, status):
        data = upload(api, post, "a.txt", b"hello").json()
        assert api("GET", f"/api/v1/attachments/{data['id']}?{query}").status == status

    @pytest.mark.integration
    @pytest.mark.parametrize("missing", ["0" * 32, "nope", "x" * 200])
    def test_unknown_ids(self, api, missing):
        assert api("GET", f"/api/v1/attachments/{missing}").status == 404
        assert api("GET", f"/api/v1/attachments/{missing}/download").status == 404

    @pytest.mark.integration
    def test_the_token_can_read_files_on_drafts(self, site, api):
        site.store.create_post("Draft", "x")
        data = upload(api, "draft", "wip.py", CODE).json()
        assert api("GET", f"/api/v1/attachments/{data['id']}").json()["content"] == CODE.decode()

    @pytest.mark.integration
    def test_download(self, api, post):
        data = upload(api, post, "helpers.py", CODE).json()
        response = api("GET", f"/api/v1/attachments/{data['id']}/download")
        assert response.status == 200 and response.body == CODE
        assert response.headers["content-type"] == "application/octet-stream"
        assert response.headers["content-disposition"].startswith("attachment")


class TestRemoving:
    @pytest.mark.integration
    def test_remove_deletes_the_record_and_the_file(self, site, api, post):
        data = upload(api, post, "a.txt", b"x").json()
        response = api("DELETE", f"/api/v1/posts/{post}/attachments/{data['id']}")
        assert response.status == 200 and response.json() == {"slug": post, "id": data["id"], "deleted": True}
        assert site.store.list_attachments(post) == [] and not site.blog.attachments.path(data["id"]).exists()
        assert api("DELETE", f"/api/v1/posts/{post}/attachments/{data['id']}").status == 404

    @pytest.mark.integration
    def test_a_file_cannot_be_removed_through_another_post(self, site, api, post):
        site.store.create_post("Other", "x")
        data = upload(api, post, "a.txt", b"x").json()
        assert api("DELETE", f"/api/v1/posts/other/attachments/{data['id']}").status == 404
        assert len(site.store.list_attachments(post)) == 1

    @pytest.mark.integration
    def test_unknown_post(self, api):
        response = api("DELETE", f"/api/v1/posts/ghost/attachments/{'0' * 32}")
        assert response.status == 404 and "not found" in response.json()["error"]

    @pytest.mark.integration
    def test_deleting_a_post_through_the_api_deletes_its_files(self, site, api, post):
        upload(api, post, "a.txt", b"x")
        upload(api, post, "b.txt", b"y")
        assert len(list((site.settings.data_dir / "attachments").iterdir())) == 2
        api("DELETE", f"/api/v1/posts/{post}")
        assert list((site.settings.data_dir / "attachments").iterdir()) == []


class TestPostsCarryTheirAttachments:
    @pytest.mark.integration
    def test_a_full_post_lists_its_files_with_links(self, site, api, post):
        data = upload(api, post, "helpers.py", CODE).json()
        full = api("GET", f"/api/v1/posts/{post}").json()
        assert full["attachment_count"] == 1
        assert full["attachments"][0]["id"] == data["id"] and full["attachments"][0]["url"] == f"{site.url}/files/{data['id']}"
        assert full["attachments"][0]["view_url"].endswith("/view")

    @pytest.mark.integration
    def test_summaries_only_carry_a_count(self, api, post):
        upload(api, post, "a.txt", b"x")
        upload(api, post, "b.txt", b"x")
        listed = api("GET", "/api/v1/posts").json()["posts"][0]
        searched = api("GET", "/api/v1/search?q=text").json()["posts"][0]
        assert listed["attachment_count"] == searched["attachment_count"] == 2
        assert "attachments" not in listed and "attachments" not in searched

    @pytest.mark.integration
    def test_a_post_without_files(self, api, post):
        full = api("GET", f"/api/v1/posts/{post}").json()
        assert full["attachment_count"] == 0 and full["attachments"] == []

    @pytest.mark.integration
    def test_attaching_does_not_change_the_posts_version(self, api, post):
        before = api("GET", f"/api/v1/posts/{post}").json()["version"]
        upload(api, post, "a.txt", b"x")
        assert api("GET", f"/api/v1/posts/{post}").json()["version"] == before

    @pytest.mark.integration
    def test_links_use_the_public_address_when_one_is_set(self, make_site):
        site = make_site(public_url="https://blog.example.com/")
        site.store.create_post("Host", "x", publish=True)
        data = upload(site.browser().api, "host", "a.txt", b"x").json()
        assert data["url"] == f"https://blog.example.com/files/{data['id']}"

    @pytest.mark.integration
    def test_files_survive_renaming_the_post(self, api, post):
        upload(api, post, "a.txt", b"x")
        api("PATCH", f"/api/v1/posts/{post}", json_body={"slug": "renamed"})
        assert api("GET", "/api/v1/posts/renamed/attachments").json()["count"] == 1


class TestApiAndWebsiteTogether:
    @pytest.mark.integration
    def test_a_file_attached_by_a_tool_can_be_downloaded_in_the_browser(self, site, api, post):
        data = upload(api, post, "analysis.py", CODE).json()
        admin = site.admin()
        assert "analysis.py" in admin.get(f"/post/{post}").text
        assert admin.get(f"/files/{data['id']}").body == CODE
        assert "def total" in admin.get(f"/files/{data['id']}/view").text

    @pytest.mark.integration
    def test_a_file_attached_in_the_editor_is_readable_by_a_tool(self, site, api, post):
        admin = site.admin()
        csrf = admin.csrf(f"/admin/edit/{post}")
        admin.post(f"/admin/attach/{post}", files={"file": ("from-browser.txt", b"typed in a browser")}, headers={"X-CSRF-Token": csrf})
        listing = api("GET", f"/api/v1/posts/{post}/attachments").json()["attachments"]
        assert api("GET", f"/api/v1/attachments/{listing[0]['id']}").json()["content"] == "typed in a browser"
