"""HTML for every page of the blog.

Every value interpolated into markup goes through ``_e`` (HTML escaping) or
``_q`` (URL path escaping). Post bodies arrive already rendered, with raw HTML
escaped, by ``render.render_markdown``. Pages never contain inline scripts or
styles: the stylesheet and the editor script are served from /static.

``ctx`` is a dict: ``site`` (title, description), ``user`` (the logged-in
username or None), ``csrf`` (the session's CSRF token or None).
"""

import html
from datetime import datetime
from math import ceil
from urllib.parse import quote, urlencode


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


def _csrf_field(ctx: dict) -> str:
    return f'<input type="hidden" name="csrf" value="{_e(ctx.get("csrf") or "")}">'


def layout(ctx: dict, title: str, content: str, query: str = "", editor: bool = False, nav: bool = True) -> str:
    """Wrap page content in the shared shell: header, navigation, search box."""
    site = ctx["site"]
    page_title = f"{title} · {site['title']}" if title else site["title"]
    description = f'<p class="tagline">{_e(site["description"])}</p>' if site.get("description") else ""
    script = '<script src="/static/admin.js" defer></script>' if editor else ""
    if not nav:
        navigation = ""
    else:
        if ctx.get("user"):
            account = (
                '<a href="/admin">Dashboard</a><a href="/admin/new">New post</a>'
                f'<form method="post" action="/logout" class="inline">{_csrf_field(ctx)}'
                '<button type="submit" class="link">Log out</button></form>'
            )
        else:
            account = '<a href="/login">Log in</a>'
        navigation = (
            '<nav class="main"><a href="/">Posts</a><a href="/tags">Tags</a>'
            f'{account}'
            '<form action="/search" method="get" role="search" class="search">'
            f'<input type="search" name="q" value="{_e(query)}" placeholder="Search" aria-label="Search"></form></nav>'
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
{'' if ctx.get('indexable') else '<meta name="robots" content="noindex, nofollow">'}
<title>{_e(page_title)}</title>
<link rel="stylesheet" href="/static/blog.css">
{script}
</head>
<body class="{'wide' if editor else ''}">
<div class="wrap">
<header class="site">
<h1><a href="/">{_e(site['title'])}</a></h1>
{description}
{navigation}
</header>
<main>
{content}
</main>
</div>
</body>
</html>
"""


# --- reading pages -----------------------------------------------------------

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


def _entry(post: dict, show_draft_badge: bool = True) -> str:
    badge = ' <span class="badge">Draft</span>' if show_draft_badge and post["status"] == "draft" else ""
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

    if page == 1 and page * page_size >= total:
        return ""
    newer = link(page - 1, "← Newer") if page > 1 else "<span></span>"
    older = link(page + 1, "Older →") if page * page_size < total else "<span></span>"
    return f'<nav class="pager">{newer}{older}</nav>'


def post_list(ctx: dict, heading: str, listing: dict, base: str, page: int, page_size: int, empty: str) -> str:
    """A paginated list of published posts (home and tag pages)."""
    entries = "".join(_entry(post) for post in listing["posts"]) or f'<p class="empty">{_e(empty)}</p>'
    content = f"<h2>{_e(heading)}</h2>{entries}{_pager(base, page, listing['total'], page_size)}"
    return layout(ctx, heading if base != "/" else "", content)


def post_page(ctx: dict, post: dict, body_html: str) -> str:
    banner = ""
    if post["status"] == "draft":
        banner = '<p class="banner">This post is a draft. Only you can see it.</p>'
    edit = ""
    if ctx.get("user"):
        edit = f'<p class="meta"><a href="/admin/edit/{_q(post["slug"])}">Edit this post</a></p>'
    content = (
        f'<article><h1>{_e(post["title"])}</h1><p class="meta">{_meta(post)}</p>{edit}{banner}'
        f'<div class="post-body">{body_html}</div></article>'
    )
    return layout(ctx, post["title"], content)


def tags_page(ctx: dict, tags: list[dict]) -> str:
    items = "".join(f'<li><a href="/tag/{_q(t["tag"])}">#{_e(t["tag"])}</a> <span class="meta">{t["count"]}</span></li>' for t in tags)
    body = f'<ul class="tags">{items}</ul>' if items else '<p class="empty">No tags yet.</p>'
    return layout(ctx, "Tags", f"<h2>Tags</h2>{body}")


def search_page(ctx: dict, query: str, posts: list[dict] | None) -> str:
    if posts is None:
        body = '<p class="empty">Type a word or phrase to search.</p>'
    elif not posts:
        body = f'<p class="empty">No posts match “{_e(query)}”.</p>'
    else:
        body = "".join(_entry(post) for post in posts)
    return layout(ctx, "Search", f"<h2>Search</h2>{body}", query=query)


def message_page(ctx: dict, title: str, message: str) -> str:
    return layout(ctx, title, f'<h2>{_e(title)}</h2><p class="empty">{_e(message)}</p>')


def not_found_page(ctx: dict, message: str = "That page does not exist.") -> str:
    return message_page(ctx, "Not found", message)


# --- login -------------------------------------------------------------------

def login_page(ctx: dict, error: str = "", next_url: str = "/admin", username: str = "") -> str:
    banner = f'<p class="banner error" role="alert">{_e(error)}</p>' if error else ""
    content = f"""<h2>Log in</h2>{banner}
<form method="post" action="/login" class="card login">
<input type="hidden" name="next" value="{_e(next_url)}">
<label>Username <input name="username" value="{_e(username)}" autocomplete="username" required{'' if username else ' autofocus'}></label>
<label>Password <input type="password" name="password" autocomplete="current-password" required{' autofocus' if username else ''}></label>
<button type="submit" class="primary">Log in</button>
</form>"""
    return layout(ctx, "Log in", content, nav=False)


# --- admin -------------------------------------------------------------------

def _action_form(ctx: dict, action: str, slug: str, label: str, confirm: str = "", css: str = "") -> str:
    confirm_attr = f' data-confirm="{_e(confirm)}"' if confirm else ""
    return (
        f'<form method="post" action="/admin/{action}/{_q(slug)}" class="inline"{confirm_attr}>{_csrf_field(ctx)}'
        f'<button type="submit" class="link {css}">{label}</button></form>'
    )


def dashboard_page(ctx: dict, listing: dict, stats: dict, status: str, page: int, page_size: int, notice: str = "") -> str:
    def tab(value: str, label: str, count: int) -> str:
        href = "/admin" if value == "all" else f"/admin?status={value}"
        current = ' aria-current="page" class="current"' if value == status else ""
        return f'<a href="{href}"{current}>{label} <span class="count">{count}</span></a>'

    tabs = (
        '<nav class="tabs">' + tab("all", "All", stats["total"]) + tab("draft", "Drafts", stats["drafts"])
        + tab("published", "Published", stats["published"]) + "</nav>"
    )
    rows = []
    for post in listing["posts"]:
        slug = post["slug"]
        toggle = (_action_form(ctx, "unpublish", slug, "Unpublish") if post["status"] == "published"
                  else _action_form(ctx, "publish", slug, "Publish"))
        date = post["published_at"] if post["status"] == "published" else post["updated_at"]
        rows.append(
            f'<tr><td><a href="/admin/edit/{_q(slug)}"><strong>{_e(post["title"])}</strong></a>'
            f'<div class="meta">/{_e(slug)}</div></td>'
            f'<td><span class="badge {_e(post["status"])}">{_e(post["status"])}</span></td>'
            f'<td class="meta">{_e(format_date(date))}</td>'
            f'<td class="actions"><a href="/post/{_q(slug)}">View</a> <a href="/admin/edit/{_q(slug)}">Edit</a> {toggle} '
            f'{_action_form(ctx, "delete", slug, "Delete", confirm="Delete this post permanently?", css="danger")}</td></tr>'
        )
    if rows:
        table = ('<table class="posts"><thead><tr><th>Post</th><th>Status</th><th>Date</th><th></th></tr></thead><tbody>'
                 + "".join(rows) + "</tbody></table>")
    else:
        table = '<p class="empty">Nothing here yet. <a href="/admin/new">Write your first post.</a></p>'
    flash = f'<p class="banner ok" role="status">{_e(notice)}</p>' if notice else ""
    extra = {"status": status} if status != "all" else None
    head = ('<div class="head"><h2>Dashboard</h2><a class="button primary" href="/admin/new">New post</a></div>')
    return layout(ctx, "Dashboard", head + flash + tabs + table + _pager("/admin", page, listing["total"], page_size, extra))


def editor_page(ctx: dict, post: dict | None, form: dict, error: str = "", notice: str = "") -> str:
    """The post editor. `form` holds the field values to show; `post` is the saved post when editing."""
    editing = post is not None
    action = f"/admin/edit/{_q(post['slug'])}" if editing else "/admin/new"
    banner = f'<p class="banner error" role="alert">{_e(error)}</p>' if error else ""
    flash = f'<p class="banner ok" role="status">{_e(notice)}</p>' if notice else ""
    version = f'<input type="hidden" name="version" value="{_e(post["version"])}">' if editing else ""
    status = post["status"] if editing else "new"
    buttons = ['<button type="submit" name="action" value="save" class="primary">Save draft</button>' if status in ("new", "draft")
               else '<button type="submit" name="action" value="save" class="primary">Save changes</button>']
    if status in ("new", "draft"):
        buttons.append('<button type="submit" name="action" value="publish">Publish</button>')
    else:
        buttons.append('<button type="submit" name="action" value="unpublish">Unpublish</button>')
    view = f'<a class="button" href="/post/{_q(post["slug"])}">View</a>' if editing else ""
    heading = "Edit post" if editing else "New post"
    state = f'<span class="badge {_e(status)}">{_e(status)}</span>' if editing else ""
    delete = ""
    if editing:
        button = _action_form(ctx, "delete", post["slug"], "Delete this post", confirm="Delete this post permanently?", css="danger")
        delete = f'<div class="danger-zone">{button}</div>'
    content = f"""<div class="head"><h2>{heading} {state}</h2></div>{banner}{flash}
<form method="post" action="{action}" id="editor" class="editor" data-csrf="{_e(ctx.get('csrf') or '')}">
{_csrf_field(ctx)}{version}
<label>Title <input name="title" value="{_e(form.get('title', ''))}" maxlength="200" required autofocus></label>
<div class="row">
<label>Slug <input name="slug" value="{_e(form.get('slug', ''))}" maxlength="100" placeholder="Made from the title if empty"></label>
<label>Tags <input name="tags" value="{_e(form.get('tags', ''))}" placeholder="comma, separated"></label>
</div>
<label>Summary <textarea name="summary" rows="2" maxlength="500"
placeholder="Optional. Shown in lists; defaults to the start of the post.">{_e(form.get('summary', ''))}</textarea></label>
<div class="panes">
<div class="pane">
<div class="pane-head"><span>Markdown</span>
<span class="tools"><label class="button small" for="image-file">Add image</label>
<input id="image-file" type="file" accept="image/png,image/jpeg,image/gif,image/webp" hidden>
<span id="upload-status" class="meta" role="status"></span></span></div>
<textarea id="body" name="body" rows="26" spellcheck="true">{_e(form.get('body', ''))}</textarea>
</div>
<div class="pane">
<div class="pane-head"><span>Preview</span></div>
<div id="preview" class="post-body preview" aria-live="polite"></div>
</div>
</div>
<div class="bar">{''.join(buttons)}{view}<span class="meta hint">Ctrl/⌘+S saves</span></div>
</form>{delete}"""
    return layout(ctx, heading, content, editor=True)
