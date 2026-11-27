"""Run the blog.

This is the program that hosts the blog. It needs nothing else running; the MCP
server in ../blog_mcp is a separate program that manages posts through this
blog's JSON API.
"""

import sys

import uvicorn
from dotenv import load_dotenv

from blog_app import Settings, create_app

load_dotenv()

_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def main() -> None:
    settings = Settings.from_env()
    app = create_app(settings)
    blog = app.state.blog
    scheme = "https" if settings.tls_cert else "http"
    shown_host = "127.0.0.1" if settings.host in ("0.0.0.0", "") else settings.host
    mode = "public: published posts are readable by anyone" if settings.public else "private: everything needs a login"
    sys.stderr.write(
        f"[blog] {settings.title!r} is running at {scheme}://{shown_host}:{settings.port}  ({mode})\n"
        f"[blog] log in as '{settings.username}'; password: {blog.password_source}\n"
        f"[blog] API token for the MCP server: {blog.api_token_source}\n"
    )
    if settings.host not in _LOOPBACK and not settings.tls_cert:
        sys.stderr.write(
            f"[blog] WARNING: listening on {settings.host} without TLS, so logins cross the network in clear text. "
            "Set BLOG_TLS_CERT/BLOG_TLS_KEY, or put the blog behind an HTTPS reverse proxy.\n"
        )
    sys.stderr.flush()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        ssl_certfile=settings.tls_cert or None,
        ssl_keyfile=settings.tls_key or None,
        log_level="warning",
        access_log=False,
    )


if __name__ == "__main__":
    main()
