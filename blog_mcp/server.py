import sys

from dotenv import load_dotenv
from fastmcp import FastMCP

from blog_client import BlogClient, BlogServer

load_dotenv()

_client = BlogClient()
_web = BlogServer(_client)
_web.start()

sys.stderr.write(
    f"[blog] viewer: {_web.base_url}  (user: {_web.username}, password: {_web.password_source})\n"
)
sys.stderr.flush()

mcp = FastMCP("blog")


def _with_url(post: dict) -> dict:
    post["url"] = _web.post_url(post["slug"])
    return post


@mcp.tool
def create_post(title: str, body: str = "", tags: list[str] = [], slug: str = "",
                summary: str = "", publish: bool = False) -> dict:
    """Create a blog post. It is saved as a draft unless publish is true.

    Args:
        title: Post title.
        body: Post content in Markdown. Raw HTML is shown as text, not rendered.
        tags: Tags for the post (e.g. ["python", "notes"]). Lowercased automatically.
        slug: URL slug (empty to derive one from the title).
        summary: Short summary shown in lists (empty to use the start of the body).
        publish: Publish immediately instead of saving a draft.

    Returns:
        Dict with slug, title, status, tags, summary, word_count, created_at,
        updated_at, published_at, body, and the viewer url.
    """
    return _with_url(_client.create_post(title, body, tags=tags, slug=slug, summary=summary, publish=publish))


@mcp.tool
def get_post(slug: str) -> dict:
    """Get one post, including its full Markdown body.

    Args:
        slug: The post's slug, as returned by create_post or list_posts.

    Returns:
        Dict with the post's fields, body, and viewer url.
    """
    return _with_url(_client.get_post(slug))


@mcp.tool
def list_posts(status: str = "all", tag: str = "", limit: int = 20, offset: int = 0) -> dict:
    """List posts, newest first, without their bodies.

    Args:
        status: "all", "draft", or "published".
        tag: Only posts with this tag (empty for any).
        limit: Max posts to return (1-100, default 20).
        offset: Number of posts to skip, for paging.

    Returns:
        Dict with posts (each with a viewer url), total, limit, and offset.
    """
    result = _client.list_posts(status=status, tag=tag, limit=limit, offset=offset)
    result["posts"] = [_with_url(post) for post in result["posts"]]
    return result


@mcp.tool
def update_post(slug: str, title: str = "", body: str = "", summary: str = "", tags: list[str] = [],
                clear_tags: bool = False, new_slug: str = "") -> dict:
    """Change a post. Fields left empty are not modified.

    To change part of a long body, use replace_in_post instead of resending it.

    Args:
        slug: Slug of the post to change.
        title: New title (empty to keep).
        body: New full Markdown body, replacing the old one (empty to keep).
        summary: New summary (empty to keep).
        tags: New complete tag list, replacing the old one (empty to keep).
        clear_tags: Remove all tags. Ignored if tags is given.
        new_slug: New URL slug (empty to keep).

    Returns:
        Dict with the updated post, including body and viewer url.
    """
    return _with_url(_client.update_post(
        slug, title=title, body=body, summary=summary,
        tags=tags if tags else ([] if clear_tags else None),
        new_slug=new_slug,
    ))


@mcp.tool
def replace_in_post(slug: str, find: str, replace: str, replace_all: bool = False) -> dict:
    """Find and replace text in a post's body.

    Fails if the text is not found, or if it appears more than once and
    replace_all is false. Include surrounding words to make it unique.

    Args:
        slug: Slug of the post to change.
        find: Exact text to look for.
        replace: Text to put in its place (empty to delete it).
        replace_all: Replace every occurrence, not just a single one.

    Returns:
        Dict with the updated post, its viewer url, and replacements (count).
    """
    return _with_url(_client.replace_in_post(slug, find, replace, replace_all=replace_all))


@mcp.tool
def publish_post(slug: str) -> dict:
    """Publish a draft so it appears on the blog's home page.

    Args:
        slug: Slug of the post to publish.

    Returns:
        Dict with the updated post (status "published") and viewer url.
    """
    return _with_url(_client.set_status(slug, "published"))


@mcp.tool
def unpublish_post(slug: str) -> dict:
    """Return a published post to draft so it leaves the home page.

    Args:
        slug: Slug of the post to unpublish.

    Returns:
        Dict with the updated post (status "draft") and viewer url.
    """
    return _with_url(_client.set_status(slug, "draft"))


@mcp.tool
def delete_post(slug: str) -> dict:
    """Permanently delete a post. This cannot be undone.

    Args:
        slug: Slug of the post to delete.

    Returns:
        Dict with slug and deleted (false if no such post existed).
    """
    return {"slug": slug, "deleted": _client.delete_post(slug)}


@mcp.tool
def search_posts(query: str, status: str = "all", limit: int = 20) -> dict:
    """Search post titles, summaries, bodies, and tags. Every word in the query must match.

    Args:
        query: Words to look for, case-insensitive.
        status: "all", "draft", or "published".
        limit: Max posts to return (1-50, default 20).

    Returns:
        Dict with query, posts (each with a snippet of matching text and a viewer url), and count.
    """
    result = _client.search_posts(query, status=status, limit=limit)
    result["posts"] = [_with_url(post) for post in result["posts"]]
    return result


@mcp.tool
def list_tags(status: str = "all") -> dict:
    """List all tags with how many posts use each.

    Args:
        status: Count only "draft" or "published" posts, or "all".

    Returns:
        Dict with tags (list of tag and count, most used first) and count.
    """
    return _client.list_tags(status=status)


@mcp.tool
def get_blog_info() -> dict:
    """Get the blog's title, viewer address, storage location, and post counts.

    The viewer password is never returned; password_source says where it is kept.

    Returns:
        Dict with title, description, viewer_url, viewer_username, password_source,
        data_dir, and posts (total, published, drafts, tags).
    """
    return {
        "title": _web.site["title"],
        "description": _web.site["description"],
        "viewer_url": _web.base_url,
        "viewer_username": _web.username,
        "password_source": _web.password_source,
        "data_dir": str(_client.data_dir),
        "posts": _client.stats(),
    }


if __name__ == "__main__":
    if sys.stdin.isatty():
        mcp.run(transport="http", host="127.0.0.1", port=9410, path="/mcp")
    else:
        mcp.run()
