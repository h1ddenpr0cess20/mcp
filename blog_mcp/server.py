import sys
from urllib.parse import urlsplit

from dotenv import load_dotenv
from fastmcp import FastMCP

from blog_client import BlogClient, BlogUnreachable

load_dotenv()

# This server only manages posts, by calling the blog's JSON API. The blog is a separate
# program (blog_mcp/blog/blog.py); it hosts the website and keeps working when this server is off.
_client = BlogClient()

if urlsplit(_client.base_url).scheme == "http" and urlsplit(_client.base_url).hostname not in ("127.0.0.1", "localhost", "::1"):
    sys.stderr.write(f"[blog-mcp] WARNING: {_client.base_url} is plain HTTP, so the API token crosses the network in clear text.\n")
    sys.stderr.flush()

mcp = FastMCP("blog")


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
        Dict with slug, title, status, tags, summary, word_count, version, created_at,
        updated_at, published_at, body, and the post's url on the blog.
    """
    return _client.create_post(title, body, tags=tags, slug=slug, summary=summary, publish=publish)


@mcp.tool
def get_post(slug: str) -> dict:
    """Get one post, including its full Markdown body.

    Args:
        slug: The post's slug, as returned by create_post or list_posts.

    Returns:
        Dict with the post's fields, body, and url on the blog.
    """
    return _client.get_post(slug)


@mcp.tool
def list_posts(status: str = "all", tag: str = "", limit: int = 20, offset: int = 0) -> dict:
    """List posts, newest first, without their bodies.

    Args:
        status: "all", "draft", or "published".
        tag: Only posts with this tag (empty for any).
        limit: Max posts to return (1-100, default 20).
        offset: Number of posts to skip, for paging.

    Returns:
        Dict with posts (each with a url on the blog), total, limit, and offset.
    """
    return _client.list_posts(status=status, tag=tag, limit=limit, offset=offset)


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
        Dict with the updated post, including body and url.
    """
    return _client.update_post(
        slug, title=title or None, body=body or None, summary=summary or None,
        tags=tags if tags else ([] if clear_tags else None), new_slug=new_slug or None,
    )


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
        Dict with the updated post, its url, and replacements (count).
    """
    return _client.replace_in_post(slug, find, replace, replace_all=replace_all)


@mcp.tool
def publish_post(slug: str) -> dict:
    """Publish a draft so it appears on the blog's home page.

    Args:
        slug: Slug of the post to publish.

    Returns:
        Dict with the updated post (status "published") and url.
    """
    return _client.set_status(slug, "published")


@mcp.tool
def unpublish_post(slug: str) -> dict:
    """Return a published post to draft so it leaves the home page.

    Args:
        slug: Slug of the post to unpublish.

    Returns:
        Dict with the updated post (status "draft") and url.
    """
    return _client.set_status(slug, "draft")


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
        Dict with query, posts (each with a snippet of matching text and a url), and count.
    """
    return _client.search_posts(query, status=status, limit=limit)


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
def upload_image(file_path: str, alt_text: str = "") -> dict:
    """Upload an image from this computer to the blog so a post can show it.

    Accepts PNG, JPEG, GIF, and WebP up to 8 MB. Put the returned markdown in a post body.

    Args:
        file_path: Path of the image file on the machine this server runs on.
        alt_text: Short description of the image for screen readers.

    Returns:
        Dict with url (the image's address on the blog), absolute_url, and markdown to paste into a post.
    """
    result = _client.upload_image(file_path)
    alt = alt_text.replace("[", "").replace("]", "").replace("\n", " ")
    result["markdown"] = f"![{alt}]({result['url']})"
    return result


@mcp.tool
def get_blog_info() -> dict:
    """Check the blog: its title, address, whether it is running, and post counts.

    The blog is a separate program. If blog_running is false, it needs to be started
    (python blog_mcp/blog/blog.py) before post urls will open.

    Returns:
        Dict with blog_url, blog_running, and, when it is running, title, description,
        public (whether visitors can read published posts), and posts (total, published, drafts, tags).
    """
    try:
        info = _client.info()
    except BlogUnreachable as exc:
        return {"blog_url": _client.base_url, "blog_running": False, "message": str(exc)}
    return {
        "blog_url": info["url"], "blog_running": True, "title": info["title"], "description": info["description"],
        "public": info["public"], "posts": info["posts"],
    }


if __name__ == "__main__":
    if sys.stdin.isatty():
        mcp.run(transport="http", host="127.0.0.1", port=9900, path="/mcp")
    else:
        mcp.run()
