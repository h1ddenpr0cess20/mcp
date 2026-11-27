"""Machine-readable views of a public blog, for search engines and AI agents.

Plain functions that turn posts into Markdown pages, an ``llms.txt`` index, Atom and JSON feeds, a
sitemap, and schema.org data. They only format what they are given: deciding which posts a visitor
may see (published only, and only on a public blog) is done by the caller.
"""

import html
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote

MAX_LISTED = 1000  # most posts named in llms.txt and the sitemap
FEED_ITEMS = 50  # posts carried in full by the feeds
MAX_FULL_BYTES = 2_000_000  # llms-full.txt stops adding posts after this much text

ATOM = "http://www.w3.org/2005/Atom"
SITEMAP = "http://www.sitemaps.org/schemas/sitemap/0.9"

_RELATIVE_LINK = re.compile(r"\]\(/(?!/)")
# Characters XML 1.0 cannot carry: most C0 control characters and the two noncharacters U+FFFE/U+FFFF.
_XML_FORBIDDEN = re.compile(
    "[" + "".join(re.escape(chr(c)) for c in (*range(0x00, 0x09), 0x0B, 0x0C, *range(0x0E, 0x20), 0xFFFE, 0xFFFF)) + "]"
)


def one_line(text: str) -> str:
    """Collapse any whitespace, so a summary fits on one line of a list."""
    return re.sub(r"\s+", " ", text or "").strip()


def absolutize_markdown(text: str, base: str) -> str:
    """Turn site-relative Markdown links (`](/files/…)`) into absolute ones, so a post still works away from the site.

    Code blocks are left exactly as written.
    """
    out, in_fence = [], False
    for line in (text or "").split("\n"):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
        out.append(line if in_fence else _RELATIVE_LINK.sub(f"]({base}/", line))
    return "\n".join(out)


def post_url(base: str, slug: str) -> str:
    return f"{base}/post/{quote(slug, safe='')}"


def _date(timestamp: str | None) -> str:
    return (timestamp or "")[:10]


def _attachment_line(attachment: dict, base: str) -> str:
    where = f"{base}/files/{attachment['id']}" + ("/raw" if attachment.get("is_text") else "")
    kind = "text, readable as is" if attachment.get("is_text") else "download"
    return f"- [{attachment['filename']}]({where}): {attachment['size']} bytes, {attachment['content_type']} ({kind})"


def post_markdown(post: dict, base: str) -> str:
    """A post as a Markdown document: front matter, the text, and a list of its files."""
    front = {
        "title": post["title"],
        "url": post_url(base, post["slug"]),
        "published": post.get("published_at") or "",
        "updated": post.get("updated_at") or "",
        "tags": post.get("tags", []),
        "summary": one_line(post.get("summary", "")),
    }
    lines = ["---"] + [f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in front.items() if value != ""] + ["---", ""]
    body = absolutize_markdown(post.get("body", ""), base).strip()
    if not body.startswith("# "):
        lines += [f"# {post['title']}", ""]
    lines += [body, ""] if body else []
    if post.get("attachments"):
        lines += ["## Attachments", ""] + [_attachment_line(a, base) for a in post["attachments"]] + [""]
    return "\n".join(lines).rstrip() + "\n"


def llms_txt(site: dict, posts: list[dict], base: str) -> str:
    """The blog's index for language models, in the llms.txt convention."""
    about = one_line(site.get("description", "")) or f"Posts from {site['title']}."
    lines = [
        f"# {site['title']}", "", f"> {about}", "",
        f"{len(posts)} published posts, newest first. Each link is the Markdown version of the post: plain text, with no "
        "navigation or scripts. Files attached to a post are listed at the end of its Markdown.",
        "", "## Posts", "",
    ]
    for post in posts[:MAX_LISTED]:
        details = [_date(post.get("published_at"))] + (["tags: " + ", ".join(post["tags"])] if post.get("tags") else [])
        summary = one_line(post.get("summary", ""))
        link = f"[{post['title']}]({post_url(base, post['slug'])}.md)"
        lines.append(f"- {link}: {summary} ({', '.join(details)})" if summary else f"- {link} ({', '.join(details)})")
    if not posts:
        lines.append("Nothing has been published yet.")
    lines += [
        "", "## Feeds and indexes", "",
        f"- [Atom feed]({base}/feed.xml): the {FEED_ITEMS} newest posts, with their full text",
        f"- [JSON Feed]({base}/feed.json): the same posts as JSON",
        f"- [Sitemap]({base}/sitemap.xml): every published post",
        f"- [Everything in one file]({base}/llms-full.txt): the Markdown of every post, one after another",
        "",
    ]
    return "\n".join(lines)


def llms_full_txt(site: dict, posts, base: str) -> str:
    """Every post's Markdown in one document, newest first, up to a size limit. `posts` may be a lazy iterable."""
    parts = [f"# {site['title']}: all posts\n\n> {one_line(site.get('description', '')) or 'Every published post, newest first.'}\n"]
    size = len(parts[0])
    for post in posts:
        chunk = post_markdown(post, base)
        if size + len(chunk) > MAX_FULL_BYTES:
            parts.append(f"\n(Older posts are left out to keep this file small. See {base}/llms.txt for all of them.)\n")
            break
        parts.append("\n---\n\n" + chunk)
        size += len(chunk)
    return "".join(parts)


def search_markdown(query: str, posts: list[dict], base: str) -> str:
    """Search results as a Markdown list, for agents."""
    lines = [f"# Search results for “{one_line(query)}”", "", f"{len(posts)} matching posts.", ""]
    for post in posts:
        snippet = one_line(post.get("snippet") or post.get("summary", ""))
        lines.append(f"- [{post['title']}]({post_url(base, post['slug'])}.md): {snippet}")
    return "\n".join(lines) + "\n"


def _xml_text(value) -> str:
    return _XML_FORBIDDEN.sub("", str(value))


def _serialize(root: ET.Element) -> str:
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def sitemap_xml(posts: list[dict], base: str) -> str:
    """A sitemap of the home page and every published post."""
    ET.register_namespace("", SITEMAP)
    urlset = ET.Element(f"{{{SITEMAP}}}urlset")
    newest = max((p["updated_at"] for p in posts), default=None)
    entries = [(f"{base}/", newest)] + [(post_url(base, p["slug"]), p["updated_at"]) for p in posts]
    for location, modified in entries[: MAX_LISTED + 1]:
        url = ET.SubElement(urlset, f"{{{SITEMAP}}}url")
        ET.SubElement(url, f"{{{SITEMAP}}}loc").text = _xml_text(location)
        if modified:
            ET.SubElement(url, f"{{{SITEMAP}}}lastmod").text = modified
    return _serialize(urlset)


def atom_feed(site: dict, posts: list[dict], base: str, render_html) -> str:
    """An Atom feed of the newest posts with their full content. `render_html` turns Markdown into safe HTML."""
    ET.register_namespace("", ATOM)
    feed = ET.Element(f"{{{ATOM}}}feed")
    ET.SubElement(feed, f"{{{ATOM}}}title").text = _xml_text(site["title"])
    if site.get("description"):
        ET.SubElement(feed, f"{{{ATOM}}}subtitle").text = _xml_text(site["description"])
    ET.SubElement(feed, f"{{{ATOM}}}id").text = f"{base}/"
    ET.SubElement(feed, f"{{{ATOM}}}updated").text = max((p["updated_at"] for p in posts), default="1970-01-01T00:00:00Z")
    ET.SubElement(feed, f"{{{ATOM}}}link", {"rel": "self", "type": "application/atom+xml", "href": f"{base}/feed.xml"})
    ET.SubElement(feed, f"{{{ATOM}}}link", {"rel": "alternate", "type": "text/html", "href": f"{base}/"})
    ET.SubElement(ET.SubElement(feed, f"{{{ATOM}}}author"), f"{{{ATOM}}}name").text = _xml_text(site["title"])
    for post in posts[:FEED_ITEMS]:
        url = post_url(base, post["slug"])
        entry = ET.SubElement(feed, f"{{{ATOM}}}entry")
        ET.SubElement(entry, f"{{{ATOM}}}title").text = _xml_text(post["title"])
        ET.SubElement(entry, f"{{{ATOM}}}id").text = url
        ET.SubElement(entry, f"{{{ATOM}}}link", {"rel": "alternate", "type": "text/html", "href": url})
        ET.SubElement(entry, f"{{{ATOM}}}link", {"rel": "alternate", "type": "text/markdown", "href": url + ".md"})
        ET.SubElement(entry, f"{{{ATOM}}}published").text = post.get("published_at") or post["created_at"]
        ET.SubElement(entry, f"{{{ATOM}}}updated").text = post["updated_at"]
        for tag in post.get("tags", []):
            ET.SubElement(entry, f"{{{ATOM}}}category", {"term": _xml_text(tag)})
        ET.SubElement(entry, f"{{{ATOM}}}summary").text = _xml_text(one_line(post.get("summary", "")))
        html = render_html(absolutize_markdown(post.get("body", ""), base))
        ET.SubElement(entry, f"{{{ATOM}}}content", {"type": "html"}).text = _xml_text(html)
        for attachment in post.get("attachments", []):
            ET.SubElement(entry, f"{{{ATOM}}}link", {"rel": "enclosure", "type": attachment["content_type"],
                                                    "href": f"{base}/files/{attachment['id']}", "length": str(attachment["size"]),
                                                    "title": _xml_text(attachment["filename"])})
    return _serialize(feed)


def json_feed(site: dict, posts: list[dict], base: str, render_html) -> str:
    """A JSON Feed (version 1.1) of the newest posts, with Markdown and HTML content."""
    items = []
    for post in posts[:FEED_ITEMS]:
        url = post_url(base, post["slug"])
        body = absolutize_markdown(post.get("body", ""), base)
        item = {
            "id": url, "url": url, "title": post["title"], "summary": one_line(post.get("summary", "")),
            "content_html": render_html(body), "content_text": body,
            "date_published": post.get("published_at") or post["created_at"], "date_modified": post["updated_at"],
            "tags": post.get("tags", []), "_markdown_url": url + ".md",
        }
        if post.get("attachments"):
            item["attachments"] = [{"url": f"{base}/files/{a['id']}", "mime_type": a["content_type"], "title": a["filename"],
                                    "size_in_bytes": a["size"]} for a in post["attachments"]]
        items.append(item)
    feed = {"version": "https://jsonfeed.org/version/1.1", "title": site["title"], "home_page_url": f"{base}/",
            "feed_url": f"{base}/feed.json", "items": items}
    if site.get("description"):
        feed["description"] = site["description"]
    return json.dumps(feed, ensure_ascii=False, indent=2)


def json_ld(post: dict, site: dict, base: str) -> dict:
    """schema.org data describing a post, for search engines and agents."""
    url = post_url(base, post["slug"])
    data = {
        "@context": "https://schema.org", "@type": "BlogPosting", "headline": post["title"], "url": url, "mainEntityOfPage": url,
        "datePublished": post.get("published_at") or post["created_at"], "dateModified": post["updated_at"],
        "description": one_line(post.get("summary", "")), "wordCount": post.get("word_count", 0),
        "keywords": ", ".join(post.get("tags", [])),
        "isPartOf": {"@type": "Blog", "name": site["title"], "url": f"{base}/"},
    }
    if post.get("attachments"):
        data["associatedMedia"] = [{"@type": "MediaObject", "name": a["filename"], "contentUrl": f"{base}/files/{a['id']}",
                                    "encodingFormat": a["content_type"], "contentSize": f"{a['size']} B"} for a in post["attachments"]]
    return data


def safe_json_for_html(data: dict) -> str:
    """JSON for a <script type="application/ld+json"> block. `<`, `>` and `&` are escaped so no value can close the tag."""
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def agent_discovery_links() -> str:
    """<link> tags on every page of a public blog, pointing agents and readers at the feeds and the index."""
    return (
        '<link rel="alternate" type="application/atom+xml" title="Atom feed" href="/feed.xml">'
        '<link rel="alternate" type="application/feed+json" title="JSON Feed" href="/feed.json">'
        '<link rel="alternate" type="text/plain" title="llms.txt" href="/llms.txt">'
        '<link rel="sitemap" type="application/xml" title="Sitemap" href="/sitemap.xml">'
    )



def home_head(site: dict, base: str) -> str:
    """<head> tags for a public blog's home page."""
    about = html.escape(one_line(site.get("description", "")) or f"Posts from {site['title']}.", quote=True)
    return (f'<link rel="canonical" href="{html.escape(base, quote=True)}/"><meta name="description" content="{about}">'
            f'<meta property="og:type" content="website"><meta property="og:title" content="{html.escape(site["title"], quote=True)}">'
            f'<meta property="og:description" content="{about}"><meta property="og:url" content="{html.escape(base, quote=True)}/">')


def post_head(post: dict, site: dict, base: str) -> str:
    """<head> tags for a public post: canonical address, description, social tags, a Markdown alternate, and schema.org data."""
    url = html.escape(post_url(base, post["slug"]), quote=True)
    title = html.escape(post["title"], quote=True)
    about = html.escape(one_line(post.get("summary", "")), quote=True)
    published = html.escape(post.get("published_at") or post["created_at"], quote=True)
    return (
        f'<link rel="canonical" href="{url}"><link rel="alternate" type="text/markdown" title="Markdown" href="{url}.md">'
        f'<meta name="description" content="{about}"><meta property="og:type" content="article">'
        f'<meta property="og:title" content="{title}"><meta property="og:description" content="{about}">'
        f'<meta property="og:url" content="{url}"><meta property="og:site_name" content="{html.escape(site["title"], quote=True)}">'
        f'<meta property="article:published_time" content="{published}">'
        f'<script type="application/ld+json">{safe_json_for_html(json_ld(post, site, base))}</script>'
    )
