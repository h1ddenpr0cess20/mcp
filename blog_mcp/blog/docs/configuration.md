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

The first time it starts, it prints your login, including the generated password, once:

```
[blog] 'Private Blog' is running at http://127.0.0.1:9901  (private: everything needs a login)
[blog] Log in with:
[blog]     username: owner
[blog]     password: <your generated password>
[blog] That password was just generated and saved to /home/you/mcp-blog/blog_password. It is only printed this once.
[blog] The MCP server uses the API token in the file /home/you/mcp-blog/api_token
```

On later starts it only says where the password is stored. The password is printed only when the blog is started from an interactive terminal, never into a log or a service's output, so if you run it as a service, read the password from the file.

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
| `blog_password` | Generated login password (only when `BLOG_PASSWORD` is unset) |
| `api_token`     | Generated API token (only when `BLOG_API_TOKEN` is unset) |
| `secret_key`    | Key that signs login sessions |

A new `BLOG_DIR` is created with mode `0700` and the files in it are `0600`. A directory that already exists is left as it is, so pointing `BLOG_DIR` at a shared folder does not change its permissions.

Limits: titles up to 200 characters, summaries up to 500, bodies up to 1,000,000, up to 20 tags per post (50 characters each), and images up to 8 MB.

---

## Logging In and Changing the Password

| Variable         | Default       | Description |
|------------------|---------------|-------------|
| `BLOG_USERNAME`  | `owner`       | Login name (must not contain `:`) |
| `BLOG_PASSWORD`  | *(generated)* | Login password |

With `BLOG_PASSWORD` unset, a random password is generated the first time and kept in `$BLOG_DIR/blog_password`. To pick your own, set `BLOG_PASSWORD` (nothing is then written to disk), or replace the contents of that file.

Restart the blog after changing the password. Everyone who was logged in is signed out, because sessions are tied to the password.

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
