# Blog MCP Server (FastMCP)

FastMCP server that lets an AI assistant manage a [blog](../blog/README.md): write, edit, publish, search, and delete posts, and upload images. The blog is a separate program with its own website and editor. This server only talks to it through its JSON API, so the blog works fine with this server off, and you can keep editing in the browser while an assistant edits too.

## Quickstart

```bash
# From the repo root (mcp/)
pip install -r blog/requirements.txt
python blog/blog.py                      # the blog; leave it running

pip install -r blog_mcp/requirements.txt
python blog_mcp/server.py                # the MCP server
```

The MCP server runs on HTTP transport at `127.0.0.1:9900` by default. When the blog runs on the same computer with default settings, the server finds the blog's API token by itself; otherwise set `BLOG_URL` and `BLOG_API_TOKEN` (see [Configuration](#configuration)).

## Tools

### Writing
- **`create_post`** — Create a post from Markdown. Saved as a draft unless `publish` is true.
- **`update_post`** — Change a post's title, body, summary, tags, or slug.
- **`replace_in_post`** — Find and replace text in a post body without resending the whole post.
- **`upload_image`** — Upload an image from this computer and get Markdown to put in a post.

### Publishing
- **`publish_post`** — Make a draft visible on the blog's home page.
- **`unpublish_post`** — Return a published post to draft.
- **`delete_post`** — Permanently delete a post.

### Reading
- **`get_post`** — Fetch one post with its full Markdown body.
- **`list_posts`** — List posts (no bodies), filtered by status or tag, with paging.
- **`search_posts`** — Search titles, summaries, bodies, and tags, with match snippets.
- **`list_tags`** — List all tags with post counts.
- **`get_blog_info`** — Whether the blog is running, its address, title, and post counts.

## Configuration

Copy `.env.example` to `.env` and edit as needed.

| Variable | Default | Description |
|---|---|---|
| `BLOG_URL` | `http://127.0.0.1:9901` | Address of the blog |
| `BLOG_API_TOKEN` | *(from file)* | The blog's API token. If unset, read from `$BLOG_DIR/api_token` |
| `BLOG_DIR` | `~/mcp-blog` | Only used to find the token file when the blog is on this computer |
| `BLOG_TIMEOUT` | `30` | Seconds to wait for the blog |
| `BLOG_VERIFY_TLS` | `true` | Set `false` to accept a self-signed HTTPS certificate |

To manage a blog on another machine, set `BLOG_URL` to its `https://` address and `BLOG_API_TOKEN` to its token. The server warns on startup if you point it at plain `http://` on another machine, because the token would cross the network in clear text.

## How It Behaves

- **The blog must be running** for tools to work. If it is not, tools fail with a message saying how to start it, and `get_blog_info` reports `blog_running: false` instead of failing.
- **Nothing is stored here.** Posts, images, and passwords live in the blog. This server keeps no data and never sees the login password.
- **Safe with browser edits.** The blog refuses edits based on stale information. If you and an assistant edit the same post at once, the browser editor warns you and keeps your text.
- **Redirects are not followed**, so the API token is never sent anywhere other than the address you configured.
- Errors from the blog come through as short messages the assistant can act on (for example `Post 'x' not found`).

## Code Structure

- `blog_client/client.py`: `BlogClient` — calls the blog's API with `requests` and turns failures into clear errors.
- `server.py`: FastMCP tool definitions.

## Notes

- Posts are identified by slug. `create_post` returns it, and `list_posts` shows it for every post.
- Every post the tools return includes a `url`. It opens on the blog, behind its login unless the blog is public.
- Tags are lowercased and joined with hyphens (`"Machine Learning"` becomes `machine-learning`).
- See `server.py` for transport options (HTTP, SSE, stdio).
- More detail: [`docs/configuration.md`](docs/configuration.md), [`docs/tools.md`](docs/tools.md), [`docs/examples.md`](docs/examples.md).
