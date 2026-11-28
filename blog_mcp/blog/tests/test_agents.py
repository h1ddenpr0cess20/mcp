"""The agent-friendly side of a public blog, over real HTTP: llms.txt, Markdown pages, feeds, sitemap, structured data."""

import json
import re
import xml.etree.ElementTree as ET

import pytest

ATOM = "{http://www.w3.org/2005/Atom}"
SITEMAP = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
BROWSER = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
MARKDOWN = {"Accept": "text/markdown"}
SECRET = "TOP SECRET DRAFT BODY"
MACHINE_ENDPOINTS = ["/llms.txt", "/llms-full.txt", "/sitemap.xml", "/feed.xml", "/feed.json"]
CODE = b"def total(values):\n    return sum(values)\n"


def populate(site):
    site.store.create_post("First post", "Hello **world**. Read [the notes](/post/second-post).", tags=["intro"],
                           summary="The first one.", publish=True)
    site.store.create_post("Second post", "More text.", tags=["intro", "extra"], publish=True)
    site.store.create_post("Secret draft", SECRET, tags=["wip"], summary="Never shown to agents.")


def attach(admin, slug, name, content):
    return admin.post(f"/admin/attach/{slug}", files={"file": (name, content)},
                      headers={"Accept": "application/json", "X-CSRF-Token": admin.csrf(f"/admin/edit/{slug}")})


@pytest.fixture
def pub(public_site):
    populate(public_site)
    return public_site


class TestPublicIndexes:
    @pytest.mark.integration
    def test_llms_txt_indexes_the_published_posts(self, pub):
        response = pub.browser().get("/llms.txt")
        assert response.status == 200 and response.headers["content-type"] == "text/plain; charset=utf-8"
        text = response.text
        assert text.startswith("# Test Blog\n\n> Notes for testing") and f"{pub.url}/post/first-post.md" in text
        assert "The first one." in text and "tags: intro" in text and "Secret draft" not in text

    @pytest.mark.integration
    def test_llms_full_txt_carries_every_published_post_and_no_draft(self, pub):
        text = pub.browser().get("/llms-full.txt").text
        assert "Hello **world**" in text and "More text." in text and SECRET not in text and "Secret draft" not in text
        assert f"]({pub.url}/post/second-post)" in text  # relative links made absolute

    @pytest.mark.integration
    def test_sitemap_lists_the_home_page_and_published_posts(self, pub):
        response = pub.browser().get("/sitemap.xml")
        assert response.status == 200 and response.headers["content-type"].startswith("application/xml")
        locations = [u.find(f"{SITEMAP}loc").text for u in ET.fromstring(response.body)]
        assert locations[0] == f"{pub.url}/" and set(locations[1:]) == {f"{pub.url}/post/first-post", f"{pub.url}/post/second-post"}

    @pytest.mark.integration
    def test_atom_feed_is_valid_and_complete(self, pub):
        response = pub.browser().get("/feed.xml")
        assert response.status == 200 and response.headers["content-type"].startswith("application/atom+xml")
        entries = ET.fromstring(response.body).findall(f"{ATOM}entry")
        assert {e.find(f"{ATOM}title").text for e in entries} == {"First post", "Second post"}
        first = next(e for e in entries if e.find(f"{ATOM}title").text == "First post")
        assert "<strong>world</strong>" in first.find(f"{ATOM}content").text and first.find(f"{ATOM}summary").text == "The first one."

    @pytest.mark.integration
    def test_json_feed_is_valid_and_complete(self, pub):
        response = pub.browser().get("/feed.json")
        assert response.status == 200 and response.headers["content-type"].startswith("application/feed+json")
        feed = response.json()
        assert feed["version"].startswith("https://jsonfeed.org/version/1")
        assert {i["title"] for i in feed["items"]} == {"First post", "Second post"}
        item = next(i for i in feed["items"] if i["title"] == "First post")
        assert item["content_text"].startswith("Hello **world**") and item["_markdown_url"] == f"{pub.url}/post/first-post.md"

    @pytest.mark.integration
    @pytest.mark.parametrize("path", MACHINE_ENDPOINTS)
    def test_a_draft_never_appears_anywhere(self, pub, path):
        body = pub.browser().get(path).text
        assert "Secret draft" not in body and SECRET not in body and "secret-draft" not in body and "Never shown to agents" not in body

    @pytest.mark.integration
    @pytest.mark.parametrize("path", MACHINE_ENDPOINTS)
    def test_unpublishing_removes_a_post_at_once(self, pub, path):
        mention = "second-post" if path == "/sitemap.xml" else "Second post"  # the sitemap names posts by address only
        assert mention in pub.browser().get(path).text
        pub.store.set_status("second-post", "draft")
        assert mention not in pub.browser().get(path).text

    @pytest.mark.integration
    @pytest.mark.parametrize("path", MACHINE_ENDPOINTS)
    def test_the_newest_post_comes_first(self, pub, path):
        pub.store.create_post("Newest post", "latest", publish=True)
        newest, older = ("newest-post", "first-post") if path == "/sitemap.xml" else ("Newest post", "First post")
        body = pub.browser().get(path).text
        assert body.index(newest) < body.index(older)

    @pytest.mark.integration
    def test_an_empty_blog_gives_valid_empty_documents(self, public_site):
        anon = public_site.browser()
        assert "Nothing has been published yet." in anon.get("/llms.txt").text
        assert ET.fromstring(anon.get("/sitemap.xml").body).tag == f"{SITEMAP}urlset"
        assert ET.fromstring(anon.get("/feed.xml").body).findall(f"{ATOM}entry") == []
        assert anon.get("/feed.json").json()["items"] == []

    @pytest.mark.integration
    def test_hostile_text_cannot_break_the_documents(self, public_site):
        title = 'A & B <script>alert(1)</script> "quoted" \x00\x0b'
        public_site.store.create_post(title, "</script><script>alert(2)</script> body & <b>", summary="s & <i>", publish=True)
        anon = public_site.browser()
        ET.fromstring(anon.get("/feed.xml").body)  # still well-formed XML
        ET.fromstring(anon.get("/sitemap.xml").body)
        assert json.loads(anon.get("/feed.json").body)["items"]  # still valid JSON
        assert "<script>" not in anon.get("/feed.xml").text.replace("&lt;script&gt;", "")


class TestCaching:
    @pytest.mark.integration
    def test_anonymous_reads_of_a_public_blog_may_be_cached_briefly(self, pub):
        for path in MACHINE_ENDPOINTS:
            response = pub.browser().get(path)
            assert response.headers["cache-control"] == "public, max-age=300" and response.headers["etag"].startswith('"'), path

    @pytest.mark.integration
    @pytest.mark.parametrize("path", MACHINE_ENDPOINTS + ["/post/first-post.md"])
    def test_a_matching_etag_gets_a_304_with_no_body(self, pub, path):
        anon = pub.browser()
        etag = anon.get(path).headers["etag"]
        again = anon.get(path, headers={"If-None-Match": etag})
        assert again.status == 304 and again.body == b""

    @pytest.mark.integration
    def test_a_stale_etag_gets_the_new_content_after_a_change(self, pub):
        anon = pub.browser()
        etag = anon.get("/llms.txt").headers["etag"]
        pub.store.set_status("second-post", "draft")
        fresh = anon.get("/llms.txt", headers={"If-None-Match": etag})
        assert fresh.status == 200 and "Second post" not in fresh.text and fresh.headers["etag"] != etag

    @pytest.mark.integration
    def test_the_same_content_has_the_same_etag(self, pub):
        assert pub.browser().get("/llms.txt").headers["etag"] == pub.browser().get("/llms.txt").headers["etag"]

    @pytest.mark.integration
    def test_the_owner_is_never_given_a_shared_cache_header(self, pub):
        response = pub.admin().get("/llms.txt")
        assert response.status == 200 and "public" not in response.headers["cache-control"]

    @pytest.mark.integration
    def test_a_draft_in_markdown_is_never_cacheable(self, pub):
        response = pub.admin().get("/post/secret-draft.md")
        assert response.status == 200 and "public" not in response.headers["cache-control"]


class TestMarkdownPages:
    @pytest.mark.integration
    def test_the_md_address_serves_markdown(self, pub):
        response = pub.browser().get("/post/first-post.md")
        assert response.status == 200 and response.headers["content-type"] == "text/markdown; charset=utf-8"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.text.startswith("---\ntitle: \"First post\"\nurl: ") and "# First post" in response.text
        assert "Hello **world**" in response.text and f"]({pub.url}/post/second-post)" in response.text

    @pytest.mark.integration
    def test_accept_markdown_on_the_normal_address_serves_markdown(self, pub):
        response = pub.browser().get("/post/first-post", headers=MARKDOWN)
        assert response.status == 200 and response.headers["content-type"].startswith("text/markdown")
        assert response.headers["vary"] == "Accept" and response.text == pub.browser().get("/post/first-post.md").text

    @pytest.mark.integration
    def test_a_browser_still_gets_html(self, pub):
        response = pub.browser().get("/post/first-post", headers={"Accept": BROWSER})
        assert response.headers["content-type"].startswith("text/html") and "<article>" in response.text

    @pytest.mark.integration
    @pytest.mark.parametrize("accept,expect_markdown", [
        ("text/markdown", True), ("text/markdown, text/html;q=0.5", True), ("text/html, text/markdown", False),
        ("*/*", False), ("", False), ("application/json", False), ("text/html", False),
    ])
    def test_which_representation_is_chosen(self, pub, accept, expect_markdown):
        response = pub.browser().get("/post/first-post", headers={"Accept": accept})
        assert response.headers["content-type"].startswith("text/markdown") is expect_markdown

    @pytest.mark.integration
    def test_the_home_page_in_markdown_is_the_llms_index(self, pub):
        response = pub.browser().get("/", headers=MARKDOWN)
        assert response.text == pub.browser().get("/llms.txt").text and response.headers["vary"] == "Accept"

    @pytest.mark.integration
    def test_search_in_markdown(self, pub):
        response = pub.browser().get("/search?q=hello", headers=MARKDOWN)
        assert response.status == 200 and response.headers["content-type"].startswith("text/markdown")
        assert f"[First post]({pub.url}/post/first-post.md)" in response.text and "Second post" not in response.text

    @pytest.mark.integration
    def test_search_in_markdown_never_includes_drafts_for_a_visitor(self, pub):
        assert "Secret draft" not in pub.browser().get("/search?q=secret", headers=MARKDOWN).text

    @pytest.mark.integration
    def test_unknown_posts_are_plain_text_404s_not_html_pages(self, pub):
        for response in (pub.browser().get("/post/ghost.md"), pub.browser().get("/post/ghost", headers=MARKDOWN)):
            assert response.status == 404 and response.headers["content-type"].startswith("text/plain") and "<html" not in response.text

    @pytest.mark.integration
    def test_a_draft_is_invisible_in_markdown_to_visitors_but_not_to_the_owner(self, pub):
        for response in (pub.browser().get("/post/secret-draft.md"), pub.browser().get("/post/secret-draft", headers=MARKDOWN)):
            assert response.status == 404 and SECRET not in response.text
        assert SECRET in pub.admin().get("/post/secret-draft.md").text

    @pytest.mark.integration
    def test_attachments_are_listed_with_addresses_an_agent_can_read(self, pub):
        admin = pub.admin()
        attach(admin, "first-post", "analysis.py", CODE)
        attach(admin, "first-post", "data.bin", bytes(range(256)))
        text = pub.browser().get("/post/first-post.md").text
        text_id = next(a["id"] for a in pub.store.list_attachments("first-post") if a["filename"] == "analysis.py")
        bin_id = next(a["id"] for a in pub.store.list_attachments("first-post") if a["filename"] == "data.bin")
        assert "## Attachments" in text
        assert f"[analysis.py]({pub.url}/files/{text_id}/raw)" in text and f"[data.bin]({pub.url}/files/{bin_id})" in text

    @pytest.mark.integration
    def test_front_matter_is_valid_for_hostile_titles(self, public_site):
        public_site.store.create_post('Evil"\n---\ninjected: "yes', "body", publish=True)
        slug = public_site.store.list_posts()["posts"][0]["slug"]
        block = public_site.browser().get(f"/post/{slug}.md").text.split("---\n")[1]
        assert "injected" not in {line.split(":")[0] for line in block.splitlines()}


class TestPageMetadata:
    @staticmethod
    def json_ld(html: str):
        match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        return json.loads(match.group(1)) if match else None

    @pytest.mark.integration
    def test_a_public_post_describes_itself_to_machines(self, pub):
        response = pub.browser().get("/post/first-post")
        html = response.text
        assert f'<link rel="canonical" href="{pub.url}/post/first-post">' in html
        assert f'href="{pub.url}/post/first-post.md"' in html and 'type="text/markdown"' in html
        assert 'property="og:type" content="article"' in html and 'name="description" content="The first one."' in html
        data = self.json_ld(html)
        assert data["@type"] == "BlogPosting" and data["headline"] == "First post" and data["url"] == f"{pub.url}/post/first-post"
        assert response.headers["link"] == f'<{pub.url}/post/first-post.md>; rel="alternate"; type="text/markdown"'
        assert response.headers["vary"] == "Accept"

    @pytest.mark.integration
    def test_every_public_page_links_the_feeds_and_the_index(self, pub):
        for path in ("/", "/post/first-post", "/tags", "/search?q=hello"):
            html = pub.browser().get(path).text
            for href in ("/feed.xml", "/feed.json", "/llms.txt", "/sitemap.xml"):
                assert f'href="{href}"' in html, (path, href)

    @pytest.mark.integration
    def test_the_home_page_has_a_canonical_address_and_description(self, pub):
        html = pub.browser().get("/").text
        assert f'rel="canonical" href="{pub.url}/"' in html and 'name="description" content="Notes for testing"' in html

    @pytest.mark.integration
    def test_attachments_appear_in_the_structured_data(self, pub):
        attach(pub.admin(), "first-post", "analysis.py", CODE)
        media = self.json_ld(pub.browser().get("/post/first-post").text)["associatedMedia"]
        assert media[0]["name"] == "analysis.py" and media[0]["contentUrl"].startswith(f"{pub.url}/files/")

    @pytest.mark.integration
    def test_hostile_titles_and_summaries_cannot_break_out_of_the_head(self, public_site):
        public_site.store.create_post('"><script>alert(1)</script>', "body", summary='</script><img src=x onerror=alert(2)>', publish=True)
        slug = public_site.store.list_posts()["posts"][0]["slug"]
        html = public_site.browser().get(f"/post/{slug}").text
        head = html.split("</head>")[0]
        assert "<script>alert" not in html and "<img src=x" not in html
        assert head.count("<script") == 1  # only our own JSON-LD block
        assert self.json_ld(html)["headline"] == '"><script>alert(1)</script>'

    @pytest.mark.integration
    def test_only_the_structured_data_block_is_an_inline_script_and_the_policy_still_forbids_inline_script(self, pub):
        response = pub.browser().get("/post/first-post")
        inline = re.findall(r"<script(?![^>]*\bsrc=)([^>]*)>", response.text, re.IGNORECASE)
        assert inline == [' type="application/ld+json"']
        policy = response.headers["content-security-policy"]
        assert "script-src 'self'" in policy and "unsafe-inline" not in policy

    @pytest.mark.integration
    def test_a_draft_page_is_not_described_to_machines(self, pub):
        html = pub.admin().get("/post/secret-draft").text
        assert "application/ld+json" not in html and 'rel="canonical"' not in html and 'property="og:' not in html

    @pytest.mark.integration
    def test_a_private_blog_adds_none_of_it(self, site):
        populate(site)
        html = site.admin().get("/post/first-post").text
        assert "application/ld+json" not in html and 'rel="canonical"' not in html and "/feed.xml" not in html and "/llms.txt" not in html
        assert 'name="robots" content="noindex' in html


class TestPrivateBlogsStayPrivate:
    @pytest.mark.integration
    @pytest.mark.parametrize("path", MACHINE_ENDPOINTS + ["/post/first-post.md", "/search?q=hello"])
    def test_visitors_get_a_plain_401_that_an_agent_can_understand(self, site, path):
        populate(site)
        headers = MARKDOWN if path.startswith("/search") else {}
        response = site.browser().get(path, headers=headers)
        assert response.status == 401 and response.headers["content-type"].startswith("text/plain")
        assert "private" in response.text and "First post" not in response.text and "<html" not in response.text

    @pytest.mark.integration
    def test_an_agent_asking_for_markdown_gets_a_401_not_a_login_page(self, site):
        populate(site)
        response = site.browser().get("/post/first-post", headers=MARKDOWN)
        assert response.status == 401 and "<form" not in response.text

    @pytest.mark.integration
    @pytest.mark.parametrize("path", MACHINE_ENDPOINTS)
    def test_the_owner_sees_published_posts_only(self, site, path):
        populate(site)
        body = site.admin().get(path).text
        assert ("first-post" if path == "/sitemap.xml" else "First post") in body
        assert "Secret draft" not in body and "secret-draft" not in body and SECRET not in body

    @pytest.mark.integration
    def test_robots_keeps_everyone_out(self, site):
        assert "Disallow: /\n" in site.browser().get("/robots.txt").text

    @pytest.mark.integration
    def test_the_api_token_does_not_open_the_machine_endpoints(self, site):
        populate(site)
        response = site.browser().get("/llms.txt", headers={"Authorization": "Bearer test-api-token-0123456789abcdef"})
        assert response.status == 401


class TestRobots:
    @pytest.mark.integration
    def test_a_public_blog_welcomes_crawlers_and_names_its_sitemap(self, pub):
        text = pub.browser().get("/robots.txt").text
        assert "User-agent: *\nAllow: /\n" in text
        assert all(f"Disallow: {path}" in text for path in ("/admin", "/api", "/login"))
        assert f"Sitemap: {pub.url}/sitemap.xml" in text and "/llms.txt" in text and "Disallow: /\n" not in text

    @pytest.mark.integration
    def test_the_sitemap_address_follows_the_public_url_setting(self, make_site):
        site = make_site(public=True, public_url="https://blog.example.com/")
        assert "Sitemap: https://blog.example.com/sitemap.xml" in site.browser().get("/robots.txt").text

    @pytest.mark.integration
    def test_links_use_the_public_url_setting_everywhere(self, make_site):
        site = make_site(public=True, public_url="https://blog.example.com")
        site.store.create_post("Hello", "body", publish=True)
        anon = site.browser()
        assert "https://blog.example.com/post/hello.md" in anon.get("/llms.txt").text
        assert "https://blog.example.com/post/hello" in anon.get("/sitemap.xml").text
        assert 'rel="canonical" href="https://blog.example.com/post/hello"' in anon.get("/post/hello").text
        assert site.url not in anon.get("/feed.xml").text


class TestRawTextAttachments:
    @pytest.mark.integration
    def test_code_is_served_as_plain_text_an_agent_can_read(self, pub):
        attach(pub.admin(), "first-post", "analysis.py", CODE)
        attachment_id = pub.store.list_attachments("first-post")[0]["id"]
        response = pub.browser().get(f"/files/{attachment_id}/raw")
        assert response.status == 200 and response.body == CODE
        assert response.headers["content-type"] == "text/plain; charset=utf-8" and response.headers["content-disposition"] == "inline"
        assert response.headers["x-content-type-options"] == "nosniff" and "sandbox" in response.headers["content-security-policy"]

    @pytest.mark.integration
    def test_html_and_script_files_are_still_only_ever_plain_text(self, pub):
        admin = pub.admin()
        samples = [("page.html", b"<script>alert(1)</script>"), ("logo.svg", b"<svg onload=alert(1)/>"), ("app.js", b"alert(1)")]
        for name, content in samples:
            attach(admin, "first-post", name, content)
        for record in pub.store.list_attachments("first-post"):
            response = pub.browser().get(f"/files/{record['id']}/raw")
            assert response.headers["content-type"] == "text/plain; charset=utf-8"
            assert response.headers["x-content-type-options"] == "nosniff"

    @pytest.mark.integration
    def test_a_binary_file_has_no_raw_view(self, pub):
        attach(pub.admin(), "first-post", "data.bin", bytes(range(256)))
        record = pub.store.list_attachments("first-post")[0]
        assert pub.browser().get(f"/files/{record['id']}/raw").status == 404

    @pytest.mark.integration
    def test_a_files_on_a_draft_stay_hidden(self, pub):
        attach(pub.admin(), "secret-draft", "notes.txt", b"private notes")
        record = pub.store.list_attachments("secret-draft")[0]
        response = pub.browser().get(f"/files/{record['id']}/raw")
        assert response.status == 404 and b"private notes" not in response.body
        assert pub.admin().get(f"/files/{record['id']}/raw").body == b"private notes"

    @pytest.mark.integration
    def test_on_a_private_blog_visitors_are_sent_to_log_in(self, site):
        populate(site)
        attach(site.admin(), "first-post", "a.txt", b"x")
        record = site.store.list_attachments("first-post")[0]
        response = site.browser().get(f"/files/{record['id']}/raw")
        assert response.status == 303 and response.location.startswith("/login")

    @pytest.mark.integration
    @pytest.mark.parametrize("bad", ["0" * 32, "..", "x'%20OR%20'1'='1", "a" * 32 + "%0a"])
    def test_unknown_ids(self, pub, bad):
        assert pub.browser().get(f"/files/{bad}/raw").status == 404


class TestApiInfo:
    @pytest.mark.integration
    def test_a_public_blog_tells_tools_where_agents_should_look(self, pub):
        urls = pub.browser().api("GET", "/api/v1/info").json()["agent_urls"]
        assert urls["llms_txt"] == f"{pub.url}/llms.txt" and urls["atom_feed"] == f"{pub.url}/feed.xml"
        assert urls["post_markdown"] == f"{pub.url}/post/<slug>.md" and set(urls) >= {"llms_full_txt", "json_feed", "sitemap"}

    @pytest.mark.integration
    def test_a_private_blog_offers_none(self, site):
        assert "agent_urls" not in site.browser().api("GET", "/api/v1/info").json()
