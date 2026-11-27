"""HTML page templates for the blog viewer.

Every value interpolated into markup goes through ``_e`` (HTML escaping) or
``_q`` (URL path escaping). Post bodies arrive already rendered, with raw HTML
escaped, by ``render.render_markdown``.
"""

import html
from datetime import datetime
from math import ceil
from urllib.parse import quote, urlencode

CSS = """
:root{
color-scheme:light dark;--bg:#fbfaf8;--fg:#1f2328;--muted:#6a737d;--line:#e4e1db;
--accent:#2f5d8a;--code:#f1eee8;--warn:#8a5a00;--warn-bg:#fff4d6}
@media (prefers-color-scheme:dark){:root{
--bg:#16181c;--fg:#e6e6e6;--muted:#9aa4af;--line:#2d3138;
--accent:#8ab4e0;--code:#20242a;--warn:#f0c674;--warn-bg:#2b2410}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:18px/1.65 Georgia,"Iowan Old Style","Times New Roman",serif}
a{color:var(--accent)}
.wrap{max-width:42rem;margin:0 auto;padding:1.5rem 1rem 4rem}
header.site{border-bottom:1px solid var(--line);padding-bottom:1rem;margin-bottom:2rem}
header.site h1{margin:0;font-size:1.6rem}
header.site h1 a{color:inherit;text-decoration:none}
header.site p{margin:.25rem 0 0;color:var(--muted);font-size:.95rem}
nav.main{display:flex;flex-wrap:wrap;gap:.5rem 1.25rem;align-items:center;margin-top:1rem;font:15px system-ui,sans-serif}
nav.main input{font:inherit;padding:.3rem .6rem;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}
h1,h2,h3,h4{line-height:1.25}
.entry{margin:0 0 2rem}
.entry h2{margin:0 0 .2rem;font-size:1.35rem}
.entry h2 a{text-decoration:none}
.entry p{margin:.4rem 0}
.meta{color:var(--muted);font:14px system-ui,sans-serif}
.tag{display:inline-block;margin-right:.4rem}
.badge{
font:600 11px system-ui,sans-serif;text-transform:uppercase;letter-spacing:.05em;
color:var(--warn);background:var(--warn-bg);padding:.1rem .45rem;border-radius:4px;vertical-align:middle}
.banner{font:15px system-ui,sans-serif;color:var(--warn);background:var(--warn-bg);padding:.6rem .9rem;border-radius:6px;margin:1rem 0}
.post-body img{max-width:100%;height:auto}
.post-body pre{background:var(--code);padding:1rem;overflow-x:auto;border-radius:6px;font-size:.85em;line-height:1.5}
.post-body code{background:var(--code);padding:.1em .3em;border-radius:4px;font-size:.88em}
.post-body pre code{background:none;padding:0}
.post-body blockquote{margin:1rem 0;padding:.1rem 1rem;border-left:3px solid var(--line);color:var(--muted)}
.post-body table{border-collapse:collapse;display:block;overflow-x:auto}
.post-body th,.post-body td{border:1px solid var(--line);padding:.35rem .7rem}
.pager{display:flex;justify-content:space-between;font:15px system-ui,sans-serif;margin-top:2rem}
.tags li{display:inline-block;margin:0 1rem .5rem 0;font:16px system-ui,sans-serif}
ul.tags{padding:0;list-style:none}
.empty{color:var(--muted)}
"""


def _e(value) -> str:
    return html.escape(str(value), quote=True)


def _q(value) -> str:
    return quote(str(value), safe="")


def format_date(iso: str | None) -> str:
    """Format a stored UTC timestamp as 'November 27, 2026'."""
    if not iso:
        return ""
    try:
        parsed = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return str(iso)
    return f"{parsed:%B} {parsed.day}, {parsed.year}"


def reading_minutes(word_count: int) -> int:
    return max(1, ceil((word_count or 0) / 200))


def layout(site: dict, title: str, content: str, query: str = "") -> str:
    """Wrap page content in the shared shell: header, navigation, search box."""
    page_title = f"{title} · {site['title']}" if title else site["title"]
    description = f"<p>{_e(site['description'])}</p>" if site.get("description") else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<meta name="referrer" content="no-referrer">
<title>{_e(page_title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header class="site">
<h1><a href="/">{_e(site['title'])}</a></h1>
{description}
<nav class="main">
<a href="/">Posts</a>
<a href="/drafts">Drafts</a>
<a href="/tags">Tags</a>
<form action="/search" method="get" role="search">
<input type="search" name="q" value="{_e(query)}" placeholder="Search" aria-label="Search">
</form>
</nav>
</header>
<main>
{content}
</main>
</div>
</body>
</html>
"""


def _tag_links(tags: list[str]) -> str:
    return "".join(f'<a class="tag" href="/tag/{_q(tag)}">#{_e(tag)}</a>' for tag in tags)


def _meta(post: dict) -> str:
    date = post.get("published_at") if post["status"] == "published" else post.get("updated_at")
    parts = [f'<time datetime="{_e(date or "")}">{_e(format_date(date))}</time>']
    parts.append(f"{reading_minutes(post['word_count'])} min read")
    tags = _tag_links(post["tags"])
    if tags:
        parts.append(tags)
    return " · ".join(parts)


def _entry(post: dict) -> str:
    badge = ' <span class="badge">Draft</span>' if post["status"] == "draft" else ""
    snippet = post.get("snippet") or post["summary"]
    summary = f"<p>{_e(snippet)}</p>" if snippet else ""
    return (
        f'<article class="entry"><h2><a href="/post/{_q(post["slug"])}">{_e(post["title"])}</a>{badge}</h2>'
        f'<p class="meta">{_meta(post)}</p>{summary}</article>'
    )


def _pager(base: str, page: int, total: int, page_size: int, extra: dict | None = None) -> str:
    def link(target: int, label: str) -> str:
        params = dict(extra or {})
        if target > 1:
            params["page"] = target
        href = base + (f"?{urlencode(params)}" if params else "")
        return f'<a href="{_e(href)}">{label}</a>'

    newer = link(page - 1, "← Newer") if page > 1 else "<span></span>"
    older = link(page + 1, "Older →") if page * page_size < total else "<span></span>"
    if page == 1 and page * page_size >= total:
        return ""
    return f'<nav class="pager">{newer}{older}</nav>'


def post_list(site: dict, heading: str, listing: dict, base: str, page: int, page_size: int, empty: str,
              extra: dict | None = None) -> str:
    """A paginated list of posts (home, drafts, tag pages)."""
    entries = "".join(_entry(post) for post in listing["posts"]) or f'<p class="empty">{_e(empty)}</p>'
    content = f"<h2>{_e(heading)}</h2>{entries}{_pager(base, page, listing['total'], page_size, extra)}"
    return layout(site, heading if base != "/" else "", content)


def post_page(site: dict, post: dict, body_html: str) -> str:
    banner = ""
    if post["status"] == "draft":
        banner = '<p class="banner">This post is a draft. It is only visible here, behind your password.</p>'
    content = (
        f'<article><h1>{_e(post["title"])}</h1><p class="meta">{_meta(post)}</p>{banner}'
        f'<div class="post-body">{body_html}</div></article>'
    )
    return layout(site, post["title"], content)


def tags_page(site: dict, tags: list[dict]) -> str:
    items = "".join(f'<li><a href="/tag/{_q(t["tag"])}">#{_e(t["tag"])}</a> <span class="meta">{t["count"]}</span></li>' for t in tags)
    body = f'<ul class="tags">{items}</ul>' if items else '<p class="empty">No tags yet.</p>'
    return layout(site, "Tags", f"<h2>Tags</h2>{body}")


def search_page(site: dict, query: str, posts: list[dict] | None) -> str:
    if posts is None:
        body = '<p class="empty">Type a word or phrase to search every post, drafts included.</p>'
    elif not posts:
        body = f'<p class="empty">No posts match “{_e(query)}”.</p>'
    else:
        body = "".join(_entry(post) for post in posts)
    return layout(site, "Search", f"<h2>Search</h2>{body}", query=query)


def message_page(site: dict, title: str, message: str) -> str:
    return layout(site, title, f'<h2>{_e(title)}</h2><p class="empty">{_e(message)}</p>')


def not_found_page(site: dict, message: str = "That page does not exist.") -> str:
    return message_page(site, "Not found", message)
