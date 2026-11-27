# Blog

A private blog you run yourself. Write in Markdown in your browser, keep drafts, attach images, and read it all behind a login. It is a standalone web application: start it and it works, with nothing else running. The MCP server one folder up ([`blog_mcp`](../README.md)) is a separate program that lets an AI assistant manage the same posts through the blog's API; the blog never depends on it.

## Quickstart

```bash
# From the repo root (mcp/)
pip install -r blog_mcp/blog/requirements.txt
python blog_mcp/blog/blog.py
```

Open `http://127.0.0.1:9901` and log in as `owner`. The first time the blog starts it generates a password and **prints it in the terminal, once**. Write it down: the blog stores only a salted hash of it, never the password itself, so it cannot be shown again. If you lose it, or want your own, set a new one:

```bash
python blog_mcp/blog/blog.py set-password              # type a new password
python blog_mcp/blog/blog.py set-password --generate   # or have one generated and shown once
```

Then restart the blog.

Then click **New post**. To choose your own password, title, or port, copy `blog_mcp/blog/.env.example` to `blog_mcp/blog/.env` and edit it.

## What You Get

**Writing**
- An editor with a live preview next to the text, so you see the rendered post as you type
- Drafts and publishing: save a draft, publish when ready, unpublish later
- Images: use the *Add image* button, paste from the clipboard, or drag a file into the editor
- Tags, a custom URL, and an optional summary for each post
- `Ctrl/⌘+S` saves, deleting asks first, and leaving with unsaved changes warns you
- If a post was changed elsewhere (say, by the MCP server) while you were editing it, saving is refused with a warning and your text is kept, so nothing is silently overwritten

**Managing**
- A dashboard listing every post with filters for drafts and published, and one-click publish, unpublish, and delete

**Reading**
- A clean, responsive reading layout with dark mode, tag pages, search, pagination, and reading time

**Private by default**
- A login page with a session cookie; repeated wrong passwords lock the client out for a while
- Set `BLOG_PUBLIC=true` to let anyone read published posts while drafts, the editor, and the API stay behind the login

## Configuration

Copy `.env.example` to `.env` and edit as needed.

| Variable | Default | Description |
|---|---|---|
| `BLOG_DIR` | `~/mcp-blog` | Where the blog keeps its data |
| `BLOG_TITLE` | `Private Blog` | Blog name |
| `BLOG_DESCRIPTION` | *(empty)* | Tagline under the name |
| `BLOG_HOST` | `127.0.0.1` | Address to listen on |
| `BLOG_PORT` | `9901` | Port to listen on |
| `BLOG_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated HTTP Host allowlist; add your public domain when proxied |
| `BLOG_USERNAME` | `owner` | Login name |
| `BLOG_PASSWORD` | *(none)* | A login password to hash at startup. Prefer `set-password`, so no plain text is in a config file |
| `BLOG_PASSWORD_HASH` | *(none)* | A password hash from `blog.py hash-password`; wins over `BLOG_PASSWORD` |
| `BLOG_API_TOKEN` | *(generated)* | Token for the API; unset generates one into `$BLOG_DIR/api_token` |
| `BLOG_PUBLIC` | `false` | `true` lets anyone read published posts |
| `BLOG_PUBLIC_URL` | *(from the request)* | Address used in links the API returns, when behind a proxy |
| `BLOG_TLS_CERT` / `BLOG_TLS_KEY` | *(none)* | PEM files to serve HTTPS directly |

## Hosting It

By default the blog listens on `127.0.0.1`, so only your own computer can reach it. To read it from your phone or another machine, or to leave it running all the time, see [`docs/configuration.md`](docs/configuration.md): it covers HTTPS, a reverse proxy, starting it at boot, and backups.

## The API

Everything the editor does is also available as a JSON API under `/api/v1`, protected by a bearer token, so scripts and the MCP server can manage posts. See [`docs/api.md`](docs/api.md).

## Security Notes

- **Your password is never stored.** Only a salted PBKDF2-SHA256 hash (600,000 iterations) is kept, so a copied data folder or backup does not reveal it. A password given in `BLOG_PASSWORD` is hashed at startup, and the blog holds no copy of the plain text. (An earlier version stored it as plain text. On upgrade the blog converts it to a hash and deletes the old file automatically.)
- Tokens are compared in constant time. Sessions are signed, expire after 14 days, are checked against SQLite, and are revoked server-side at logout (including copied cookies). Password changes invalidate all existing sessions.
- Requests with a Host header outside `BLOG_ALLOWED_HOSTS` are rejected before URL generation; set `BLOG_PUBLIC_URL` to the canonical HTTPS origin when using a public domain.
- Every state-changing form and background request carries a CSRF token.
- Pages never run inline scripts. The Content-Security-Policy allows scripts and styles only from the blog itself.
- Raw HTML in a post is shown as text rather than run, and `javascript:` links are not turned into links.
- Uploaded images are identified by their contents, not their file names. Only PNG, JPEG, GIF, and WebP are accepted (SVG is refused because it can carry script), and they are stored under random names.
- The database, secrets, and data directory are owner-only on creation.

What it does not do:

- It is a single-user blog. There are no accounts, comments, or feeds.
- There is no "forgot password" page. Run `python blog_mcp/blog/blog.py set-password` and restart; that also signs every session out.
- The database is not encrypted at rest. Use disk encryption if that matters to you.
- Login lockouts are kept in memory per client address, so they reset when the blog restarts.
- A post that embeds an `https://` image makes the reader's browser fetch it from that host.

## Code Structure

- `blog.py`: starts the blog (uvicorn).
- `blog_app/app.py`: routes for the website, login, admin, and API.
- `blog_app/store.py`: SQLite storage and the rules for posts.
- `blog_app/auth.py`: sessions, CSRF tokens, API token, login lockout.
- `blog_app/media.py`: image validation and storage.
- `blog_app/render.py`: Markdown rendering (raw HTML escaped).
- `blog_app/pages.py`: HTML for every page. `blog_app/static/`: the stylesheet and editor script.
