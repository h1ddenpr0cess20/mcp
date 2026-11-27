# Configuration

How to install, run, host, and back up the blog.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Blog](#running-the-blog)
- [Where Your Data Lives](#where-your-data-lives)
- [Logging In and Changing the Password](#logging-in-and-changing-the-password)
- [Private or Public](#private-or-public)
- [Reaching the Blog from Other Devices](#reaching-the-blog-from-other-devices)
- [Behind a Reverse Proxy](#behind-a-reverse-proxy)
- [Keeping It Running](#keeping-it-running)
- [Backups](#backups)
- [Connecting the MCP Server](#connecting-the-mcp-server)

---

## Requirements

- Python 3.10 or later
- No accounts, API keys, or external services

---

## Installation

### Step 1 — Clone the monorepo

```bash
git clone https://github.com/h1ddenpr0cess20/mcp.git
cd mcp
```

### Step 2 — Create and activate the virtual environment

**macOS and Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (Command Prompt):**

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### Step 3 — Install dependencies

```bash
pip install -r blog_mcp/blog/requirements.txt
```

### Step 4 — Configure (optional)

```bash
cp blog_mcp/blog/.env.example blog_mcp/blog/.env
# Edit .env to set the title, port, or password
```

---

## Running the Blog

```bash
python blog_mcp/blog/blog.py
```

The first time it starts from a terminal, it generates a password, prints your login once, and stores only a hash of the password:

```
[blog] 'Private Blog' is running at http://127.0.0.1:9901  (private: everything needs a login)
[blog] Log in with:
[blog]     username: owner
[blog]     password: <your generated password>
[blog] Write it down now: only a hash is stored (in /home/you/mcp-blog/password_hash), so it cannot be shown again.
[blog] To choose a different password later, run: python blog_mcp/blog/blog.py set-password
[blog] The MCP server uses the API token in the file /home/you/mcp-blog/api_token
```

On later starts it does not show the password; it tells you how to set a new one. The password is only ever shown to an interactive terminal, never written into a log or a service's output. If there is no password yet and the blog is not started from a terminal (for example as a service), it refuses to start and tells you to run `python blog_mcp/blog/blog.py set-password` first.

Stop it with `Ctrl+C`. If the port is already in use it stops with an error instead of starting twice; change `BLOG_PORT`.

A health check for monitors is available at `/healthz` (answers `ok`, no login needed).

---

## Where Your Data Lives

| Variable   | Default      | Description |
|------------|--------------|-------------|
| `BLOG_DIR` | `~/mcp-blog` | Directory holding everything |

| File or folder  | Description |
|-----------------|-------------|
| `blog.db`       | SQLite database: every post, tag, and timestamp |
| `media/`        | Uploaded images, under random names |
| `password_hash` | Salted hash of the login password (the password itself is never stored) |
| `api_token`     | Generated API token (only when `BLOG_API_TOKEN` is unset) |
| `secret_key`    | Key that signs login sessions |

A new `BLOG_DIR` is created with mode `0700` and the files in it are `0600`. A directory that already exists is left as it is, so pointing `BLOG_DIR` at a shared folder does not change its permissions.

Limits: titles up to 200 characters, summaries up to 500, bodies up to 1,000,000, up to 20 tags per post (50 characters each), and images up to 8 MB.

---

## Logging In and Changing the Password

| Variable              | Default | Description |
|-----------------------|---------|-------------|
| `BLOG_USERNAME`       | `owner` | Login name (must not contain `:`) |
| `BLOG_PASSWORD`       | *(none)* | A password to hash at startup (see below) |
| `BLOG_PASSWORD_HASH`  | *(none)* | A ready-made password hash; takes priority over `BLOG_PASSWORD` |

**The blog never stores your password.** It keeps a salted hash (PBKDF2-SHA256, 600,000 iterations) in `$BLOG_DIR/password_hash`, readable only by you. Anyone who gets a copy of the data folder or a backup cannot read your password from it, and cannot try guesses against it faster than the hash allows.

To set or change the password:

```bash
python blog_mcp/blog/blog.py set-password              # prompts twice (at least 8 characters)
python blog_mcp/blog/blog.py set-password --generate   # generates a strong one and shows it once
```

Restart the blog afterwards. Everyone who was logged in is signed out, because sessions are tied to the password.

**Keeping the password out of config files.** `BLOG_PASSWORD` works, but it leaves the plain text in your `.env` and in the process's environment. If you set the password in the environment, prefer a hash:

```bash
python blog_mcp/blog/blog.py hash-password
```

It asks for a password and prints a line to put in your `.env` as `BLOG_PASSWORD_HASH=...`. If either variable is set it takes priority over the stored hash.

**Upgrading from an earlier version.** Earlier versions kept the password in plain text in a file named `blog_password`. When the blog starts it converts that file to a hash, deletes the plain-text file, and tells you so. Your password stays the same. A copy of the old file in a backup is still plain text; delete or replace any such backup.

**The API token is different.** It must stay readable, because the MCP server presents it on every request and finds it in `$BLOG_DIR/api_token`. That file is owner-only, and the token only works for the API (it cannot log in to the website or the editor). If you want it out of a file, set `BLOG_API_TOKEN` yourself and give the same value to the MCP server.

Sessions last 14 days. After 5 wrong passwords from one address within 15 minutes, that address is locked out until the window passes, even if the right password is then entered.

---

## Private or Public

| Variable      | Default | Description |
|---------------|---------|-------------|
| `BLOG_PUBLIC` | `false` | Who can read published posts |

- **`false` (private):** every page needs a login, except the login page, the health check, `robots.txt`, and the static files (stylesheet and editor script). Search engines are told to stay away.
- **`true` (public):** anyone can read published posts, tag pages, search results (published only), and images. Drafts, the dashboard, the editor, and the API still need credentials. Search engines may index the pages.

Image addresses are long random names, so in public mode an image is readable by anyone who has its link, even if only a draft uses it.

---

## Reaching the Blog from Other Devices

| Variable                        | Default     | Description |
|---------------------------------|-------------|-------------|
| `BLOG_HOST`                     | `127.0.0.1` | Address to listen on |
| `BLOG_PORT`                     | `9901`      | Port |
| `BLOG_TLS_CERT`, `BLOG_TLS_KEY` | *(none)*    | PEM files; set both to serve HTTPS |

Set `BLOG_HOST=0.0.0.0` to listen on every network interface. A login sends the password, so on any network other than your own computer it must travel over HTTPS. Either use the options below, or reach the blog through an SSH tunnel or a VPN you trust.

For a quick private setup on your home network, make a self-signed certificate (your browser will ask you to trust it once):

```bash
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout ~/mcp-blog/blog.key -out ~/mcp-blog/blog.pem -subj "/CN=blog"
```

```
BLOG_HOST=0.0.0.0
BLOG_TLS_CERT=~/mcp-blog/blog.pem
BLOG_TLS_KEY=~/mcp-blog/blog.key
```

If you listen on a non-loopback address without a certificate the blog still starts, but prints a warning.

---

## Behind a Reverse Proxy

To give the blog a real domain with a trusted certificate, keep it on `127.0.0.1` and put an HTTPS proxy in front. For example, with [Caddy](https://caddyserver.com/), which obtains certificates automatically:

```
blog.example.com {
    reverse_proxy 127.0.0.1:9901
}
```

Set the address the API should use in links:

```
BLOG_PUBLIC_URL=https://blog.example.com
```

The blog trusts `X-Forwarded-Proto` and `X-Forwarded-For` only from `127.0.0.1` (uvicorn's default; change it with the `FORWARDED_ALLOW_IPS` environment variable). That is what makes the session cookie `Secure` over HTTPS and makes login lockouts apply to each visitor rather than to the proxy.

If the blog is exposed to the internet, use a long password (the generated one is) and keep `BLOG_PUBLIC=false` unless you want strangers reading it. It is built for one person's blog, not for heavy traffic.

---

## Keeping It Running

The blog is an ordinary foreground program, so use whatever you normally use to keep one running. On Linux with systemd, a unit such as this keeps it up and starts it at boot (a standard unit; adjust the paths and user, and note it has not been run under systemd as part of this repo's tests):

```ini
[Unit]
Description=Private blog
After=network.target

[Service]
User=you
WorkingDirectory=/home/you/mcp/blog_mcp/blog
ExecStart=/home/you/mcp/.venv/bin/python blog.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now blog
```

Settings come from `blog_mcp/blog/.env` (read from the folder the blog starts in) or the unit's `Environment=` lines.

---

## Backups

Everything is in `BLOG_DIR`. To back it up, copy the folder, or use SQLite's own tool for the database, which is safe to run while the blog is running:

```bash
sqlite3 ~/mcp-blog/blog.db ".backup '$HOME/blog-backup.db'"
cp -r ~/mcp-blog/media ~/blog-media-backup
```

To restore, stop the blog and put `blog.db` and `media/` back.

---

## Connecting the MCP Server

The [`blog_mcp`](../../README.md) server manages posts through the API. It needs the blog's address and API token, which it finds by itself when both run on the same computer with the default `BLOG_DIR`. See that package's documentation for other setups.
