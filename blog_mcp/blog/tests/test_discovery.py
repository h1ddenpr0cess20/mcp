"""Tests for the pure functions that build the agent-facing views: Markdown, llms.txt, feeds, sitemap, schema.org."""

import json
import xml.etree.ElementTree as ET

import pytest

from blog_app import discovery as d
from blog_app.render import render_markdown

BASE = "https://blog.example.com"
SITE = {"title": "My Blog", "description": "Notes & experiments"}
ATOM = "{http://www.w3.org/2005/Atom}"
SITEMAP = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

TEXT_FILE = {"id": "a" * 32, "filename": "analysis.py", "size": 120, "content_type": "text/x-python", "is_text": True}
BINARY_FILE = {"id": "b" * 32, "filename": "data.zip", "size": 2048, "content_type": "application/zip", "is_text": False}


def make_post(slug="hello", title="Hello", body="Body text.", **overrides):
    post = {"slug": slug, "title": title, "body": body, "summary": "A short summary.", "tags": ["a", "b"], "word_count": 2,
            "created_at": "2026-01-01T10:00:00Z", "updated_at": "2026-01-02T11:00:00Z", "published_at": "2026-01-01T10:00:00Z",
            "attachments": []}
    post.update(overrides)
    return post


def front_matter(markdown: str) -> dict:
    block = markdown.split("---\n")[1]
    return {line.split(": ", 1)[0]: json.loads(line.split(": ", 1)[1]) for line in block.strip().splitlines()}


class TestAbsolutizeMarkdown:
    @pytest.mark.unit
    @pytest.mark.parametrize("text,expected", [
        ("[a](/files/x)", f"[a]({BASE}/files/x)"),
        ("![pic](/media/p.png)", f"![pic]({BASE}/media/p.png)"),
        ("[a](https://other.example/x)", "[a](https://other.example/x)"),
        ("[a](//cdn.example/x)", "[a](//cdn.example/x)"),
        ("[a](#section)", "[a](#section)"),
        ("[a](relative/path)", "[a](relative/path)"),
        ("[one](/a) and [two](/b)", f"[one]({BASE}/a) and [two]({BASE}/b)"),
        ("no links here", "no links here"),
        ("", ""),
    ])
    def test_links(self, text, expected):
        assert d.absolutize_markdown(text, BASE) == expected

    @pytest.mark.unit
    @pytest.mark.parametrize("fence", ["```", "~~~"])
    def test_code_blocks_are_left_exactly_as_written(self, fence):
        text = f"[x](/a)\n{fence}\nmarkdown: [y](/b)\n{fence}\n[z](/c)"
        assert d.absolutize_markdown(text, BASE) == f"[x]({BASE}/a)\n{fence}\nmarkdown: [y](/b)\n{fence}\n[z]({BASE}/c)"

    @pytest.mark.unit
    def test_none(self):
        assert d.absolutize_markdown(None, BASE) == ""


class TestPostMarkdown:
    @pytest.mark.unit
    def test_front_matter_describes_the_post(self):
        meta = front_matter(d.post_markdown(make_post(), BASE))
        assert meta["title"] == "Hello" and meta["url"] == f"{BASE}/post/hello" and meta["tags"] == ["a", "b"]
        assert meta["published"] == "2026-01-01T10:00:00Z" and meta["summary"] == "A short summary."

    @pytest.mark.unit
    def test_a_heading_is_added_unless_the_text_has_its_own(self):
        assert "\n# Hello\n" in d.post_markdown(make_post(body="Just text."), BASE)
        own = d.post_markdown(make_post(body="# Hello\n\nText."), BASE)
        assert own.count("# Hello") == 1

    @pytest.mark.unit
    def test_relative_links_become_absolute(self):
        assert f"]({BASE}/files/x)" in d.post_markdown(make_post(body="[f](/files/x)"), BASE)

    @pytest.mark.unit
    def test_attachments_are_listed_with_addresses_an_agent_can_read(self):
        text = d.post_markdown(make_post(attachments=[TEXT_FILE, BINARY_FILE]), BASE)
        assert "## Attachments" in text
        assert f"[analysis.py]({BASE}/files/{'a' * 32}/raw): 120 bytes, text/x-python (text, readable as is)" in text
        assert f"[data.zip]({BASE}/files/{'b' * 32}): 2048 bytes, application/zip (download)" in text

    @pytest.mark.unit
    def test_no_attachments_section_without_attachments(self):
        assert "Attachments" not in d.post_markdown(make_post(), BASE)

    @pytest.mark.unit
    def test_a_hostile_title_cannot_break_the_front_matter(self):
        title = 'Evil"\n---\ninjected: "yes'
        meta = front_matter(d.post_markdown(make_post(title=title), BASE))
        assert meta["title"] == title and "injected" not in meta

    @pytest.mark.unit
    def test_unicode_is_kept(self):
        assert "日本語 🎉" in d.post_markdown(make_post(title="日本語 🎉"), BASE)

    @pytest.mark.unit
    def test_an_empty_body(self):
        assert d.post_markdown(make_post(body=""), BASE).endswith("# Hello\n")

    @pytest.mark.unit
    def test_ends_with_one_newline(self):
        assert d.post_markdown(make_post(), BASE).endswith("\n") and not d.post_markdown(make_post(), BASE).endswith("\n\n")


class TestLlmsTxt:
    @pytest.mark.unit
    def test_follows_the_convention(self):
        lines = d.llms_txt(SITE, [make_post()], BASE).splitlines()
        assert lines[0] == "# My Blog" and lines[2] == "> Notes & experiments"
        assert "## Posts" in lines and "## Feeds and indexes" in lines

    @pytest.mark.unit
    def test_each_post_links_to_its_markdown_with_its_summary(self):
        text = d.llms_txt(SITE, [make_post()], BASE)
        assert f"- [Hello]({BASE}/post/hello.md): A short summary. (2026-01-01, tags: a, b)" in text

    @pytest.mark.unit
    def test_a_post_without_a_summary(self):
        assert f"- [Hello]({BASE}/post/hello.md) (2026-01-01" in d.llms_txt(SITE, [make_post(summary="")], BASE)

    @pytest.mark.unit
    def test_summaries_stay_on_one_line(self):
        text = d.llms_txt(SITE, [make_post(summary="line one\n\nline   two\n- sneaky list item")], BASE)
        assert "line one line two - sneaky list item" in text and "\n- sneaky" not in text

    @pytest.mark.unit
    def test_an_empty_blog(self):
        text = d.llms_txt({"title": "Empty", "description": ""}, [], BASE)
        assert "> Posts from Empty." in text and "Nothing has been published yet." in text

    @pytest.mark.unit
    def test_points_at_the_feeds_and_the_full_export(self):
        text = d.llms_txt(SITE, [], BASE)
        for path in ("/feed.xml", "/feed.json", "/sitemap.xml", "/llms-full.txt"):
            assert f"({BASE}{path})" in text

    @pytest.mark.unit
    def test_is_capped(self):
        posts = [make_post(slug=f"p{i}", title=f"P{i}") for i in range(d.MAX_LISTED + 50)]
        assert d.llms_txt(SITE, posts, BASE).count(".md)") == d.MAX_LISTED


class TestLlmsFull:
    @pytest.mark.unit
    def test_every_post_in_order_with_separators(self):
        posts = [make_post(slug="a", title="First", body="one"), make_post(slug="b", title="Second", body="two")]
        text = d.llms_full_txt(SITE, posts, BASE)
        assert text.index("# First") < text.index("# Second") and text.count("\n---\n\n") >= 2

    @pytest.mark.unit
    def test_accepts_a_lazy_iterable(self):
        assert "# Lazy" in d.llms_full_txt(SITE, (p for p in [make_post(title="Lazy")]), BASE)

    @pytest.mark.unit
    def test_stops_at_the_size_limit_and_says_so(self, monkeypatch):
        monkeypatch.setattr(d, "MAX_FULL_BYTES", 500)
        text = d.llms_full_txt(SITE, [make_post(slug=f"p{i}", title=f"P{i}", body="x" * 200) for i in range(20)], BASE)
        assert "Older posts are left out" in text and len(text) < 1200 and f"{BASE}/llms.txt" in text

    @pytest.mark.unit
    def test_an_empty_blog(self):
        assert d.llms_full_txt(SITE, [], BASE).startswith("# My Blog: all posts")


class TestSearchMarkdown:
    @pytest.mark.unit
    def test_lists_matches_with_snippets(self):
        text = d.search_markdown("sour dough", [make_post(snippet="…my sourdough starter…")], BASE)
        assert "Search results for “sour dough”" in text and f"[Hello]({BASE}/post/hello.md): …my sourdough starter…" in text

    @pytest.mark.unit
    def test_falls_back_to_the_summary(self):
        assert "A short summary." in d.search_markdown("q", [make_post()], BASE)


class TestSitemap:
    @pytest.mark.unit
    def test_is_valid_xml_listing_the_home_page_and_each_post(self):
        root = ET.fromstring(d.sitemap_xml([make_post(), make_post(slug="two")], BASE))
        locations = [u.find(f"{SITEMAP}loc").text for u in root]
        assert root.tag == f"{SITEMAP}urlset" and locations == [f"{BASE}/", f"{BASE}/post/hello", f"{BASE}/post/two"]

    @pytest.mark.unit
    def test_lastmod_is_the_posts_update_time_and_the_home_pages_is_the_newest(self):
        posts = [make_post(updated_at="2026-03-01T00:00:00Z"), make_post(slug="o", updated_at="2026-02-01T00:00:00Z")]
        root = ET.fromstring(d.sitemap_xml(posts, BASE))
        assert [u.find(f"{SITEMAP}lastmod").text for u in root] == ["2026-03-01T00:00:00Z"] * 2 + ["2026-02-01T00:00:00Z"]

    @pytest.mark.unit
    def test_has_the_xml_declaration(self):
        assert d.sitemap_xml([], BASE).startswith('<?xml version="1.0" encoding="UTF-8"?>\n')

    @pytest.mark.unit
    def test_an_empty_blog_still_lists_the_home_page(self):
        root = ET.fromstring(d.sitemap_xml([], BASE))
        assert [u.find(f"{SITEMAP}loc").text for u in root] == [f"{BASE}/"] and root[0].find(f"{SITEMAP}lastmod") is None


class TestAtomFeed:
    def feed(self, posts, **kw):
        return ET.fromstring(d.atom_feed(SITE, posts, BASE, render_markdown, **kw))

    @pytest.mark.unit
    def test_valid_and_complete(self):
        root = self.feed([make_post(attachments=[TEXT_FILE])])
        assert root.tag == f"{ATOM}feed" and root.find(f"{ATOM}title").text == "My Blog"
        assert root.find(f"{ATOM}id").text == f"{BASE}/" and root.find(f"{ATOM}updated").text == "2026-01-02T11:00:00Z"
        entry = root.find(f"{ATOM}entry")
        assert entry.find(f"{ATOM}id").text == f"{BASE}/post/hello" and entry.find(f"{ATOM}title").text == "Hello"
        assert [c.get("term") for c in entry.findall(f"{ATOM}category")] == ["a", "b"]
        assert entry.find(f"{ATOM}summary").text == "A short summary."

    @pytest.mark.unit
    def test_entries_carry_html_markdown_alternate_and_enclosures(self):
        entry = self.feed([make_post(body="**bold** [f](/files/x)", attachments=[TEXT_FILE])]).find(f"{ATOM}entry")
        content = entry.find(f"{ATOM}content")
        assert content.get("type") == "html" and "<strong>bold</strong>" in content.text and f'href="{BASE}/files/x"' in content.text
        links = {(link.get("rel"), link.get("type")): link for link in entry.findall(f"{ATOM}link")}
        assert links[("alternate", "text/markdown")].get("href") == f"{BASE}/post/hello.md"
        enclosure = links[("enclosure", "text/x-python")]
        assert enclosure.get("href") == f"{BASE}/files/{'a' * 32}" and enclosure.get("length") == "120"

    @pytest.mark.unit
    def test_raw_html_in_a_post_is_not_passed_to_feed_readers(self):
        content = self.feed([make_post(body="<script>alert(1)</script>")]).find(f"{ATOM}entry").find(f"{ATOM}content").text
        assert "<script>" not in content and "&lt;script&gt;" in content

    @pytest.mark.unit
    def test_markup_and_control_characters_in_text_cannot_break_the_xml(self):
        root = self.feed([make_post(title="A & B <c> \x00\x0b\x1f end", summary="x\x01y", tags=["t\x02"], body="body\x03")])
        entry = root.find(f"{ATOM}entry")
        assert entry.find(f"{ATOM}title").text == "A & B <c>  end" and entry.find(f"{ATOM}summary").text == "xy"

    @pytest.mark.unit
    def test_carries_only_the_newest_posts(self):
        root = self.feed([make_post(slug=f"p{i}") for i in range(d.FEED_ITEMS + 10)])
        assert len(root.findall(f"{ATOM}entry")) == d.FEED_ITEMS

    @pytest.mark.unit
    def test_an_empty_feed_is_still_valid(self):
        root = self.feed([])
        assert root.findall(f"{ATOM}entry") == [] and root.find(f"{ATOM}updated").text

    @pytest.mark.unit
    def test_unicode(self):
        assert self.feed([make_post(title="日本語 🎉")]).find(f"{ATOM}entry").find(f"{ATOM}title").text == "日本語 🎉"


class TestJsonFeed:
    def feed(self, posts):
        return json.loads(d.json_feed(SITE, posts, BASE, render_markdown))

    @pytest.mark.unit
    def test_is_a_valid_json_feed(self):
        feed = self.feed([make_post()])
        assert feed["version"] == "https://jsonfeed.org/version/1.1" and feed["feed_url"] == f"{BASE}/feed.json"
        assert (feed["title"], feed["home_page_url"], feed["description"]) == ("My Blog", f"{BASE}/", "Notes & experiments")

    @pytest.mark.unit
    def test_items(self):
        item = self.feed([make_post(body="**hi**", attachments=[TEXT_FILE, BINARY_FILE])])["items"][0]
        assert item["id"] == item["url"] == f"{BASE}/post/hello" and item["_markdown_url"] == f"{BASE}/post/hello.md"
        assert item["content_text"] == "**hi**" and "<strong>hi</strong>" in item["content_html"] and item["tags"] == ["a", "b"]
        assert item["date_published"] == "2026-01-01T10:00:00Z" and item["date_modified"] == "2026-01-02T11:00:00Z"
        assert item["attachments"][0] == {
            "url": f"{BASE}/files/{'a' * 32}", "mime_type": "text/x-python", "title": "analysis.py", "size_in_bytes": 120,
        }

    @pytest.mark.unit
    def test_an_item_without_attachments_has_no_attachments_key(self):
        assert "attachments" not in self.feed([make_post()])["items"][0]

    @pytest.mark.unit
    def test_relative_links_are_absolute_in_both_forms(self):
        item = self.feed([make_post(body="[f](/files/x)")])["items"][0]
        assert f"]({BASE}/files/x)" in item["content_text"] and f'href="{BASE}/files/x"' in item["content_html"]

    @pytest.mark.unit
    def test_keeps_non_ascii_readable(self):
        assert "日本語" in d.json_feed(SITE, [make_post(title="日本語")], BASE, render_markdown)


class TestStructuredData:
    @pytest.mark.unit
    def test_json_ld_describes_a_blog_posting(self):
        data = d.json_ld(make_post(attachments=[TEXT_FILE]), SITE, BASE)
        assert data["@type"] == "BlogPosting" and data["@context"] == "https://schema.org"
        assert data["headline"] == "Hello" and data["url"] == f"{BASE}/post/hello" and data["keywords"] == "a, b"
        assert data["datePublished"] == "2026-01-01T10:00:00Z"
        assert data["isPartOf"] == {"@type": "Blog", "name": "My Blog", "url": f"{BASE}/"}
        assert data["associatedMedia"][0]["contentUrl"] == f"{BASE}/files/{'a' * 32}"

    @pytest.mark.unit
    def test_embedded_json_cannot_close_the_script_tag(self):
        nasty = '</script><script>alert(1)</script> & <!-- "quotes"'
        embedded = d.safe_json_for_html(d.json_ld(make_post(title=nasty, summary=nasty), SITE, BASE))
        assert "</script" not in embedded and "<script" not in embedded and "<!--" not in embedded
        assert json.loads(embedded)["headline"] == nasty  # it still means exactly the same thing to a JSON parser

    @pytest.mark.unit
    def test_post_head_escapes_attributes(self):
        head = d.post_head(make_post(title='"><script>alert(1)</script>', summary='"><img src=x onerror=alert(1)>'), SITE, BASE)
        assert "<script>alert" not in head and "<img src=x" not in head  # nothing the author wrote became markup
        assert 'content="&quot;&gt;&lt;script&gt;' in head  # it is shown as text inside its attribute
        assert head.count("<script") == 1  # only our own JSON-LD block

    @pytest.mark.unit
    def test_post_head_has_what_agents_look_for(self):
        head = d.post_head(make_post(), SITE, BASE)
        for fragment in (f'rel="canonical" href="{BASE}/post/hello"', f'type="text/markdown" title="Markdown" href="{BASE}/post/hello.md"',
                         'property="og:type" content="article"', 'name="description" content="A short summary."', "application/ld+json"):
            assert fragment in head

    @pytest.mark.unit
    def test_home_head(self):
        head = d.home_head(SITE, BASE)
        assert f'rel="canonical" href="{BASE}/"' in head and "Notes &amp; experiments" in head

    @pytest.mark.unit
    def test_discovery_links(self):
        links = d.agent_discovery_links()
        for href in ("/feed.xml", "/feed.json", "/llms.txt", "/sitemap.xml"):
            assert f'href="{href}"' in links
