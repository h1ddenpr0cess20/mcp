"""Run the blog, or manage its password.

    python blog.py                  start the blog
    python blog.py set-password     choose a new login password
    python blog.py hash-password    print a hash to use as BLOG_PASSWORD_HASH

This is the program that hosts the blog. It needs nothing else running; the MCP
server one folder up (server.py) is a separate program that manages posts through this
blog's JSON API. The blog stores only a salted hash of its password, never the password.
"""

import argparse
import getpass
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from blog_app import BlogStore, Settings, create_app, passwords
from blog_app.app import MissingPassword

load_dotenv()

_LOOPBACK = {"127.0.0.1", "localhost", "::1"}
_SET_COMMAND = "python blog_mcp/blog/blog.py set-password"


def startup_lines(settings: Settings, blog, chose_password: bool = False) -> list[str]:
    """What to tell the person starting the blog: where it is and how to log in."""
    scheme = "https" if settings.tls_cert else "http"
    host = "127.0.0.1" if settings.host in ("0.0.0.0", "") else settings.host
    mode = "public: published posts are readable by anyone" if settings.public else "private: everything needs a login"
    lines = [f"[blog] '{settings.title}' is running at {scheme}://{host}:{settings.port}  ({mode})"]
    if chose_password:
        lines += [
            f"[blog] Log in as '{settings.username}' with the password you just chose (only a hash of it is stored).",
            f"[blog] To choose a different password later, run: {_SET_COMMAND}",
        ]
    elif blog.password_source.startswith("BLOG_PASSWORD"):
        lines.append(f"[blog] Log in as '{settings.username}' with the configured password.")
    else:
        lines.append(f"[blog] Log in as '{settings.username}'. Forgotten the password? Set a new one with: {_SET_COMMAND}")
    if blog.removed_plaintext_password:
        lines.append(
            "[blog] An earlier version stored your password as plain text. It is now stored as a hash, and the plain-text file was deleted."
        )
    if settings.api_token:
        lines.append("[blog] The MCP server uses the API token set in BLOG_API_TOKEN")
    else:
        lines.append("[blog] The MCP server uses the configured API token.")
    if settings.host not in _LOOPBACK and not settings.tls_cert:
        lines.append(
            f"[blog] WARNING: listening on {settings.host} without TLS, so logins cross the network in clear text. "
            "Set BLOG_TLS_CERT/BLOG_TLS_KEY, or put the blog behind an HTTPS reverse proxy."
        )
    return lines


def _ask_new_password(ask, out) -> str | None:
    """Prompt twice for a new password. Returns None (after saying why) if it is unusable."""
    first = ask("New password: ")
    if len(first) < passwords.MIN_LENGTH:
        out.write(f"[blog] That is too short. Use at least {passwords.MIN_LENGTH} characters; longer is better.\n")
        return None
    if ask("Repeat it: ") != first:
        out.write("[blog] The two entries did not match. Nothing was changed.\n")
        return None
    return first


def set_password(settings: Settings, ask=getpass.getpass, out=None) -> int:
    """Store a new password (as a hash). Returns a process exit code."""
    out = out or sys.stderr
    password = _ask_new_password(ask, out)
    if password is None:
        return 1
    BlogStore(settings.data_dir)  # makes the data folder (owner-only) if this is a brand new blog
    path = passwords.password_file(settings.data_dir)
    passwords.write_hash(path, passwords.hash_password(password))
    (Path(settings.data_dir).expanduser() / passwords.LEGACY_PLAINTEXT_FILE).unlink(missing_ok=True)
    out.write(f"[blog] Password saved (as a hash) in {path}. Restart the blog to use it; everyone is then signed out.\n")
    if settings.password or settings.password_hash:
        out.write("[blog] Note: BLOG_PASSWORD or BLOG_PASSWORD_HASH is set and takes priority. Remove it to use the new password.\n")
    return 0


def hash_password_command(ask=getpass.getpass, out=None, stdout=None) -> int:
    """Print a password hash for BLOG_PASSWORD_HASH, so the password itself never goes into a config file."""
    out, stdout = out or sys.stderr, stdout or sys.stdout
    password = _ask_new_password(ask, out)
    if password is None:
        return 1
    stdout.write(passwords.hash_password(password) + "\n")
    out.write("[blog] Put that line in your .env as BLOG_PASSWORD_HASH=<the line above>.\n")
    return 0


def run(settings: Settings, interactive: bool, out=None, ask=getpass.getpass) -> int:
    """Start the blog. On the very first start, from a terminal, ask the person to choose a password."""
    out = out or sys.stderr
    chose_password = False
    try:
        app = create_app(settings)
    except MissingPassword:
        if not interactive:
            out.write("[blog] No login password is set up yet, and this is not an interactive terminal, so none can be asked for.\n")
            out.write(f"[blog] Run this once in a terminal, then start the blog again: {_SET_COMMAND}\n")
            return 2
        out.write("[blog] No login password is set up yet. Choose one now.\n")
        password = _ask_new_password(ask, out)
        if password is None:
            return 1
        BlogStore(settings.data_dir)  # makes the data folder (owner-only) if this is a brand new blog
        passwords.write_hash(passwords.password_file(settings.data_dir), passwords.hash_password(password))
        chose_password = True
        app = create_app(settings)
    out.write("\n".join(startup_lines(settings, app.state.blog, chose_password)) + "\n")
    out.flush()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        ssl_certfile=settings.tls_cert or None,
        ssl_keyfile=settings.tls_key or None,
        log_level="warning",
        access_log=False,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the blog, or manage its password.")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("set-password", help="choose a new login password")
    commands.add_parser("hash-password", help="print a password hash for BLOG_PASSWORD_HASH")
    args = parser.parse_args(argv)
    settings = Settings.from_env()
    if args.command == "set-password":
        return set_password(settings)
    if args.command == "hash-password":
        return hash_password_command()
    return run(settings, interactive=sys.stderr.isatty())


if __name__ == "__main__":
    sys.exit(main())
