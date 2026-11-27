"""Run the blog.

This is the program that hosts the blog. It needs nothing else running; the MCP
server one folder up (server.py) is a separate program that manages posts through this
blog's JSON API.
"""

import sys

import uvicorn
from dotenv import load_dotenv

from blog_app import Settings, create_app

load_dotenv()

_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def startup_lines(settings: Settings, blog, interactive: bool) -> list[str]:
    """What to tell the person starting the blog: where it is and exactly how to log in."""
    scheme = "https" if settings.tls_cert else "http"
    host = "127.0.0.1" if settings.host in ("0.0.0.0", "") else settings.host
    mode = "public: published posts are readable by anyone" if settings.public else "private: everything needs a login"
    lines = [f"[blog] '{settings.title}' is running at {scheme}://{host}:{settings.port}  ({mode})"]
    if blog.password_is_new and interactive:
        # Shown once, and only to a person at a terminal, never into a log file.
        lines += [
            "[blog] Log in with:",
            f"[blog]     username: {settings.username}",
            f"[blog]     password: {blog.password}",
            f"[blog] That password was just generated and saved to {blog.password_source}. It is only printed this once.",
        ]
    elif settings.password:
        lines.append(f"[blog] Log in as '{settings.username}' with the password set in BLOG_PASSWORD.")
    else:
        lines.append(f"[blog] Log in as '{settings.username}'. The password is stored in the file {blog.password_source}")
    if settings.api_token:
        lines.append("[blog] The MCP server uses the API token set in BLOG_API_TOKEN")
    else:
        lines.append(f"[blog] The MCP server uses the API token in the file {blog.api_token_source}")
    if settings.host not in _LOOPBACK and not settings.tls_cert:
        lines.append(
            f"[blog] WARNING: listening on {settings.host} without TLS, so logins cross the network in clear text. "
            "Set BLOG_TLS_CERT/BLOG_TLS_KEY, or put the blog behind an HTTPS reverse proxy."
        )
    return lines


def main() -> None:
    settings = Settings.from_env()
    app = create_app(settings)
    sys.stderr.write("\n".join(startup_lines(settings, app.state.blog, sys.stderr.isatty())) + "\n")
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
