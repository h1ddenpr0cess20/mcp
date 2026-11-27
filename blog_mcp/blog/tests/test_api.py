"""Tests for the JSON API (/api/v1), run against a real server. This is what the MCP server talks to."""

import pytest

from tests.conftest import API_TOKEN, GIF, PNG


@pytest.fixture
def api(site):
    browser = site.browser()
    return lambda method, path, **kw: browser.api(method, path, **kw)


class TestAuthentication:
    @pytest.mark.integration
    @pytest.mark.parametrize("token", [None, "", "wrong", API_TOKEN[:-1], API_TOKEN + "x", API_TOKEN.upper()])
    def test_wrong_or_missing_tokens_are_refused(self, site, token):
        response = site.browser().api("GET", "/api/v1/info", token=token)
        assert response.status == 401
        assert response.headers["www-authenticate"].startswith("Bearer")
        assert "token" in response.json()["error"]

    @pytest.mark.integration
    @pytest.mark.parametrize("header", ["Basic dGVzdDp0ZXN0", API_TOKEN, "Bearer", f"Token {API_TOKEN}"])
    def test_other_schemes_are_refused(self, site, header):
        assert site.browser().get("/api/v1/info", headers={"Authorization": header}).status == 401

    @pytest.mark.integration
    def test_a_browser_login_is_not_an_api_credential(self, site):
        admin = site.admin()
        assert admin.get("/api/v1/info").status == 401
        assert admin.get("/api/v1/posts").status == 401

    @pytest.mark.integration
    @pytest.mark.parametrize("method,path", [
        ("GET", "/api/v1/info"), ("GET", "/api/v1/posts"), ("POST", "/api/v1/posts"), ("GET", "/api/v1/posts/x"),
        ("PATCH", "/api/v1/posts/x"), ("DELETE", "/api/v1/posts/x"), ("POST", "/api/v1/posts/x/replace"),
        ("POST", "/api/v1/posts/x/publish"), ("POST", "/api/v1/posts/x/unpublish"), ("GET", "/api/v1/search?q=a"),
        ("GET", "/api/v1/tags"), ("POST", "/api/v1/media"),
    ])
    def test_every_endpoint_needs_the_token(self, site, method, path):
        site.store.create_post("X", slug="x", publish=True)
        response = site.browser().request(method, path, json_body={})
        assert response.status == 401
        assert site.store.get_post("x")["status"] == "published" and site.store.stats()["total"] == 1

    @pytest.mark.integration
    def test_the_token_can_come_from_the_environment_setting_or_a_file(self, make_site):
        site = make_site(api_token="")
        generated = (site.settings.data_dir / "api_token").read_text().strip()
        assert site.browser().api("GET", "/api/v1/info", token=generated).status == 200
        assert site.browser().api("GET", "/api/v1/info", token=API_TOKEN).status == 401


class TestInfo:
    @pytest.mark.integration
    def test_info(self, site, api):
        site.store.create_post("A", publish=True)
        data = api("GET", "/api/v1/info").json()
        assert data["title"] == "Test Blog" and data["description"] == "Notes for testing" and data["public"] is False
        assert data["url"] == site.url and data["posts"]["published"] == 1

    @pytest.mark.integration
    def test_public_url_overrides_the_address_in_links(self, make_site):
        site = make_site(public_url="https://blog.example.com/")
        api = site.browser().api
        post = api("POST", "/api/v1/posts", json_body={"title": "Hi"}).json()
        assert post["url"] == "https://blog.example.com/post/hi"
        assert api("GET", "/api/v1/info").json()["url"] == "https://blog.example.com"


class TestCreateAndRead:
    @pytest.mark.integration
    def test_create(self, site, api):
        response = api("POST", "/api/v1/posts", json_body={"title": "Hello World", "body": "Body **text**", "tags": ["Python", "#notes"],
                                                           "summary": "Sum", "slug": "custom"})
        assert response.status == 201
        post = response.json()
        assert (post["slug"], post["status"], post["tags"]) == ("custom", "draft", ["notes", "python"])
        assert (post["summary"], post["version"]) == ("Sum", 1)
        assert post["url"] == f"{site.url}/post/custom" and post["body"] == "Body **text**"
        assert site.store.get_post("custom")["title"] == "Hello World"

    @pytest.mark.integration
    def test_create_published(self, api):
        post = api("POST", "/api/v1/posts", json_body={"title": "Live", "publish": True}).json()
        assert post["status"] == "published" and post["published_at"]

    @pytest.mark.integration
    def test_slugs_are_made_unique(self, api):
        slugs = [api("POST", "/api/v1/posts", json_body={"title": "Same"}).json()["slug"] for _ in range(3)]
        assert slugs == ["same", "same-2", "same-3"]

    @pytest.mark.integration
    def test_unicode_survives(self, api):
        api("POST", "/api/v1/posts", json_body={"title": "Ünïcödé 🎉", "body": "日本語"})
        assert api("GET", "/api/v1/posts/unicode").json()["body"] == "日本語"

    @pytest.mark.integration
    @pytest.mark.parametrize("payload,message", [
        ({}, "title must not be empty"),
        ({"title": ""}, "title must not be empty"),
        ({"title": 5}, "title must be a string"),
        ({"title": "T", "body": ["x"]}, "body must be a string"),
        ({"title": "T", "tags": "python"}, "tags must be a list of strings"),
        ({"title": "T", "tags": [1, 2]}, "tags must be a list of strings"),
        ({"title": "T", "publish": "yes"}, "publish must be true or false"),
        ({"title": "T", "slug": "???"}, "slug must contain"),
        ({"title": "x" * 201}, "title is longer"),
    ])
    def test_invalid_input_is_a_400_with_a_reason(self, site, api, payload, message):
        response = api("POST", "/api/v1/posts", json_body=payload)
        assert response.status == 400 and message in response.json()["error"]
        assert site.store.stats()["total"] == 0

    @pytest.mark.integration
    @pytest.mark.parametrize("body", [b"", b"{not json", b"[1, 2]", b"null", b'"text"', b"\xff\xfe"])
    def test_malformed_bodies_are_a_400(self, api, body):
        response = api("POST", "/api/v1/posts", body=body, headers={"Content-Type": "application/json"})
        assert response.status == 400 and "JSON" in response.json()["error"]

    @pytest.mark.integration
    def test_duplicate_slug_is_a_409(self, api):
        api("POST", "/api/v1/posts", json_body={"title": "One", "slug": "taken"})
        response = api("POST", "/api/v1/posts", json_body={"title": "Two", "slug": "taken"})
        assert response.status == 409 and "already in use" in response.json()["error"]

    @pytest.mark.integration
    def test_get(self, api):
        api("POST", "/api/v1/posts", json_body={"title": "T", "body": "the body"})
        post = api("GET", "/api/v1/posts/t").json()
        assert post["body"] == "the body" and post["custom_summary"] == ""

    @pytest.mark.integration
    def test_get_missing(self, api):
        response = api("GET", "/api/v1/posts/ghost")
        assert response.status == 404 and "not found" in response.json()["error"]

    @pytest.mark.integration
    def test_list_filters_and_pages(self, site, api):
        for i in range(5):
            site.store.create_post(f"Post {i}", tags=["even" if i % 2 == 0 else "odd"], publish=i != 4)
        everything = api("GET", "/api/v1/posts").json()
        assert everything["total"] == 5 and all("url" in p and "body" not in p for p in everything["posts"])
        assert api("GET", "/api/v1/posts?status=draft").json()["total"] == 1
        assert api("GET", "/api/v1/posts?tag=even").json()["total"] == 3
        page = api("GET", "/api/v1/posts?limit=2&offset=2").json()
        assert len(page["posts"]) == 2 and (page["limit"], page["offset"]) == (2, 2)

    @pytest.mark.integration
    @pytest.mark.parametrize("query", ["status=bogus", "limit=abc", "offset=1.5", "limit="])
    def test_bad_list_parameters_are_a_400(self, api, query):
        assert api("GET", f"/api/v1/posts?{query}").status == 400

    @pytest.mark.integration
    def test_absurd_offsets_do_not_crash(self, api):
        assert api("GET", "/api/v1/posts?offset=99999999999999999999999").status == 200


class TestUpdate:
    @pytest.fixture(autouse=True)
    def _post(self, api):
        api("POST", "/api/v1/posts", json_body={"title": "Original", "body": "body", "tags": ["a"], "summary": "keep me"})

    @pytest.mark.integration
    def test_partial_update_leaves_other_fields_alone(self, api):
        post = api("PATCH", "/api/v1/posts/original", json_body={"title": "Renamed"}).json()
        assert (post["title"], post["body"], post["tags"]) == ("Renamed", "body", ["a"])
        assert (post["custom_summary"], post["version"]) == ("keep me", 2)

    @pytest.mark.integration
    def test_every_field(self, api):
        changes = {"title": "T", "body": "B", "summary": "S", "tags": ["x", "y"], "slug": "new-slug"}
        post = api("PATCH", "/api/v1/posts/original", json_body=changes).json()
        assert (post["slug"], post["title"], post["body"], post["custom_summary"], post["tags"]) == ("new-slug", "T", "B", "S", ["x", "y"])
        assert post["url"].endswith("/post/new-slug")

    @pytest.mark.integration
    def test_null_means_unchanged_and_empty_means_clear(self, api):
        post = api("PATCH", "/api/v1/posts/original", json_body={"title": None, "tags": [], "summary": ""}).json()
        assert (post["title"], post["tags"], post["custom_summary"]) == ("Original", [], "")

    @pytest.mark.integration
    def test_nothing_to_change(self, api):
        response = api("PATCH", "/api/v1/posts/original", json_body={})
        assert response.status == 400 and "Nothing to update" in response.json()["error"]

    @pytest.mark.integration
    def test_stale_expected_version_is_a_409(self, api):
        api("PATCH", "/api/v1/posts/original", json_body={"body": "edited elsewhere"})
        response = api("PATCH", "/api/v1/posts/original", json_body={"body": "stale", "expected_version": 1})
        assert response.status == 409 and "changed by someone else" in response.json()["error"]
        assert api("GET", "/api/v1/posts/original").json()["body"] == "edited elsewhere"
        assert api("PATCH", "/api/v1/posts/original", json_body={"body": "fresh", "expected_version": 2}).status == 200

    @pytest.mark.integration
    @pytest.mark.parametrize("payload", [{"expected_version": "1", "title": "x"}, {"expected_version": True, "title": "x"}, {"title": 5}])
    def test_wrong_types(self, api, payload):
        assert api("PATCH", "/api/v1/posts/original", json_body=payload).status == 400

    @pytest.mark.integration
    def test_slug_collision(self, api):
        api("POST", "/api/v1/posts", json_body={"title": "Other"})
        assert api("PATCH", "/api/v1/posts/original", json_body={"slug": "other"}).status == 409

    @pytest.mark.integration
    def test_missing_post(self, api):
        assert api("PATCH", "/api/v1/posts/ghost", json_body={"title": "x"}).status == 404


class TestReplace:
    @pytest.fixture(autouse=True)
    def _post(self, api):
        api("POST", "/api/v1/posts", json_body={"title": "T", "body": "cat and cat and dog"})

    @pytest.mark.integration
    def test_unique_match(self, api):
        post = api("POST", "/api/v1/posts/t/replace", json_body={"find": "dog", "replace": "bird"}).json()
        assert post["body"] == "cat and cat and bird" and post["replacements"] == 1

    @pytest.mark.integration
    def test_ambiguous_match_is_refused_unless_replace_all(self, api):
        response = api("POST", "/api/v1/posts/t/replace", json_body={"find": "cat", "replace": "fox"})
        assert response.status == 400 and "2 times" in response.json()["error"]
        assert api("GET", "/api/v1/posts/t").json()["body"] == "cat and cat and dog"
        done = api("POST", "/api/v1/posts/t/replace", json_body={"find": "cat", "replace": "fox", "replace_all": True}).json()
        assert done["body"] == "fox and fox and dog" and done["replacements"] == 2

    @pytest.mark.integration
    @pytest.mark.parametrize("payload,status", [({"find": "absent", "replace": "x"}, 400), ({"find": "", "replace": "x"}, 400),
                                                ({"replace": "x"}, 400), ({"find": "cat", "replace": 5}, 400),
                                                ({"find": "cat", "replace": "x", "replace_all": "yes"}, 400)])
    def test_invalid_requests(self, api, payload, status):
        assert api("POST", "/api/v1/posts/t/replace", json_body=payload).status == status

    @pytest.mark.integration
    def test_missing_post(self, api):
        assert api("POST", "/api/v1/posts/ghost/replace", json_body={"find": "a", "replace": "b"}).status == 404


class TestPublishingAndDeleting:
    @pytest.mark.integration
    def test_publish_unpublish(self, site, api):
        api("POST", "/api/v1/posts", json_body={"title": "T"})
        assert api("POST", "/api/v1/posts/t/publish").json()["status"] == "published"
        assert site.store.get_post("t")["status"] == "published"
        assert api("POST", "/api/v1/posts/t/unpublish").json()["status"] == "draft"

    @pytest.mark.integration
    @pytest.mark.parametrize("action", ["publish", "unpublish"])
    def test_missing_post(self, api, action):
        assert api("POST", f"/api/v1/posts/ghost/{action}").status == 404

    @pytest.mark.integration
    def test_delete(self, site, api):
        api("POST", "/api/v1/posts", json_body={"title": "T"})
        assert api("DELETE", "/api/v1/posts/t").json() == {"slug": "t", "deleted": True}
        assert site.store.stats()["total"] == 0
        assert api("DELETE", "/api/v1/posts/t").status == 404


class TestDiscovery:
    @pytest.mark.integration
    def test_search(self, site, api):
        site.store.create_post("Tomato notes", "Tomatoes need sun.", publish=True)
        site.store.create_post("Blight", "tomato blight")
        found = api("GET", "/api/v1/search?q=tomato").json()
        assert found["count"] == 2 and all("snippet" in p and "url" in p for p in found["posts"])
        assert api("GET", "/api/v1/search?q=tomato&status=draft").json()["count"] == 1

    @pytest.mark.integration
    @pytest.mark.parametrize("query", ["", "?q=", "?q=%20", "?q=a&limit=x", "?q=a&status=bogus"])
    def test_search_validation(self, api, query):
        assert api("GET", f"/api/v1/search{query}").status == 400

    @pytest.mark.integration
    def test_tags(self, site, api):
        site.store.create_post("A", tags=["x", "y"], publish=True)
        site.store.create_post("B", tags=["x"])
        assert api("GET", "/api/v1/tags").json()["tags"] == [{"tag": "x", "count": 2}, {"tag": "y", "count": 1}]
        assert api("GET", "/api/v1/tags?status=published").json()["tags"][0] == {"tag": "x", "count": 1}
        assert api("GET", "/api/v1/tags?status=bogus").status == 400


class TestMediaUpload:
    @pytest.mark.integration
    def test_upload(self, site, api):
        response = api("POST", "/api/v1/media", files={"file": ("pic.png", PNG)})
        assert response.status == 201
        data = response.json()
        assert data["absolute_url"] == site.url + data["url"]
        assert site.admin().get(data["url"]).body == PNG

    @pytest.mark.integration
    def test_non_images_are_refused(self, api):
        response = api("POST", "/api/v1/media", files={"file": ("x.png", b"<svg onload=alert(1)>")})
        assert response.status == 400 and "PNG, JPEG, GIF, and WebP" in response.json()["error"]

    @pytest.mark.integration
    def test_gif(self, api):
        assert api("POST", "/api/v1/media", files={"file": ("a.gif", GIF)}).json()["url"].endswith(".gif")


class TestErrors:
    @pytest.mark.integration
    def test_unknown_api_routes_are_json_404(self, api):
        response = api("GET", "/api/v1/nope")
        assert response.status == 404 and response.json() == {"error": "Not found"}

    @pytest.mark.integration
    def test_wrong_methods_are_json_405(self, site):
        response = site.browser().request("PUT", "/api/v1/posts")
        assert response.status == 405 and "error" in response.json()

    @pytest.mark.integration
    def test_unexpected_failures_are_json_500_without_details(self, site, api, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("secret internals")

        monkeypatch.setattr(site.store, "list_posts", boom)
        response = api("GET", "/api/v1/posts")
        assert response.status == 500 and "secret internals" not in response.text


class TestApiAndSiteTogether:
    @pytest.mark.integration
    def test_a_post_written_through_the_api_appears_on_the_website(self, site, api):
        api("POST", "/api/v1/posts", json_body={"title": "From the API", "body": "Hello from a tool.", "publish": True})
        page = site.admin().get("/post/from-the-api").text
        assert "Hello from a tool." in page and "From the API" in page

    @pytest.mark.integration
    def test_unpublishing_through_the_api_removes_it_from_the_home_page(self, site, api):
        api("POST", "/api/v1/posts", json_body={"title": "Brief", "publish": True})
        admin = site.admin()
        assert "Brief" in admin.get("/").text
        api("POST", "/api/v1/posts/brief/unpublish")
        assert "Brief" not in admin.get("/").text

    @pytest.mark.integration
    def test_a_post_written_on_the_website_is_readable_through_the_api(self, site, api):
        admin = site.admin()
        admin.post("/admin/new", form={"csrf": admin.csrf(), "title": "From the editor", "body": "typed in a browser", "action": "publish"})
        assert api("GET", "/api/v1/posts/from-the-editor").json()["body"] == "typed in a browser"
