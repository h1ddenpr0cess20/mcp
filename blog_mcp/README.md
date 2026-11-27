# Blog MCP Server (FastMCP)

FastMCP server for running a private blog. An AI assistant writes and manages posts through MCP tools; you read them on a built-in, password-protected web page. Posts are Markdown, kept in a local SQLite file. No API key and no external service required.

## Quickstart

```bash
# From the repo root (mcp/)
pip install -r blog_mcp/requirements.txt
cp blog_mcp/.env.example blog_mcp/.env   # optional; the defaults work
python blog_mcp/server.py
```

The MCP server runs on HTTP transport at `127.0.0.1:9410` by default, and the blog viewer at `http://127.0.0.1:9411`.

On first start the server generates a viewer password and stores it in `~/mcp-blog/viewer_password`. Log in as `owner` with that password:

```bash
cat ~/mcp-blog/viewer_password
```

## Tools

### Writing
- **`create_post`** — Create a post from Markdown. Saved as a draft unless `publish` is true.
- **`update_post`** — Change a post's title, body, summary, tags, or slug.
- **`replace_in_post`** — Find and replace text in a post body without resending the whole post.

### Publishing
- **`publish_post`** — Make a draft visible on the blog's home page.
- **`unpublish_post`** — Return a published post to draft.
- **`delete_post`** — Permanently delete a post.

### Reading
- **`get_post`** — Fetch one post with its full Markdown body.
- **`list_posts`** — List posts (no bodies), filtered by status or tag, with paging.
- **`search_posts`** — Search titles, summaries, bodies, and tags, with match snippets.
- **`list_tags`** — List all tags with post counts.
- **`get_blog_info`** — Blog title, viewer address, storage location, and post counts.

## Privacy Model

- **Password on every page.** The viewer uses HTTP Basic authentication for every request, drafts included. Passwords are compared in constant time and failed logins are slowed down.
- **Local by default.** The viewer binds to `127.0.0.1`. To reach it from another machine, set `BLOG_HOST` and enable HTTPS with `BLOG_TLS_CERT`/`BLOG_TLS_KEY`; the server warns on startup if you bind a non-loopback address without TLS.
- **Password stays out of tool output.** `get_blog_info` says where the password is kept but never returns it, so it is never sent to the model.
- **No indexing, no scripts.** Pages send `noindex`, `no-store`, and `no-referrer` headers and a Content-Security-Policy that blocks all scripts. Raw HTML in a post is shown as text, and `javascript:` links are not rendered as links.
- **Owner-only files.** A newly created data directory is `0700`; the database and password file are `0600`.

What it does not do:

- The MCP endpoint on port 9410 has no authentication, like the other servers in this repo. Anyone who can reach it can read and write every post. Keep it on `127.0.0.1`.
- The database is not encrypted at rest. Use disk encryption if that matters to you.
- Whatever MCP client you connect sees the posts it reads and writes. With a hosted model, that text goes to its provider. Pair this with a local model (for example through `subagent_mcp`) to keep posts entirely on your machine.
- A post that embeds an `https://` image makes your browser fetch it from that host.

## Configuration

Copy `.env.example` to `.env` and edit as needed.

| Variable | Default | Description |
|---|---|---|
| `BLOG_DIR` | `~/mcp-blog` | Directory for the database and generated password |
| `BLOG_TITLE` | `Private Blog` | Blog name shown in the viewer |
| `BLOG_DESCRIPTION` | *(empty)* | Tagline shown under the title |
| `BLOG_HOST` | `127.0.0.1` | Viewer bind address |
| `BLOG_PORT` | `9411` | Viewer port |
| `BLOG_USERNAME` | `owner` | Viewer login name |
| `BLOG_PASSWORD` | *(generated)* | Viewer password; leave unset to generate one into `$BLOG_DIR/viewer_password` |
| `BLOG_TLS_CERT` / `BLOG_TLS_KEY` | *(none)* | PEM certificate and key to serve the viewer over HTTPS |

## Code Structure

- `blog_client/client.py`: `BlogClient` — SQLite storage, validation, search, and tags.
- `blog_client/render.py`: Markdown rendering (raw HTML escaped) and plain-text helpers.
- `blog_client/pages.py`: HTML templates for the viewer.
- `blog_client/web.py`: `BlogServer` — the password-protected viewer.
- `server.py`: FastMCP tool definitions.

## Notes

- Posts are identified by slug. A slug is derived from the title, made unique with a numeric suffix, and can be set or renamed explicitly.
- `published_at` records when a post was first published; unpublishing and republishing keeps it.
- Tags are lowercased and joined with hyphens (`"Machine Learning"` becomes `machine-learning`).
- The viewer is read-only. Everything is edited through the MCP tools.
- See `server.py` for transport options (HTTP, SSE, stdio).
- More detail: [`docs/configuration.md`](docs/configuration.md), [`docs/tools.md`](docs/tools.md), [`docs/examples.md`](docs/examples.md).
