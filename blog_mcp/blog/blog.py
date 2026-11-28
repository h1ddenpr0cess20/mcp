"""Run the blog, or manage its password.

    python blog.py                  start the blog
    python blog.py set-password     choose a new login password (or --generate one, in a terminal)
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


def startup_lines(settings: Settings, blog, generated: str | None = None) -> list[str]:
    """What to tell the person starting the blog: where it is and exactly how to log in.

    `generated` is a password created by this very start. It is printed here and nowhere else, once.
    """
    scheme = "https" if settings.tls_cert else "http"
    host = "127.0.0.1" if settings.host in ("0.0.0.0", "") else settings.host
    mode = "public: published posts are readable by anyone" if settings.public else "private: everything needs a login"
    lines = [f"[blog] '{settings.title}' is running at {scheme}://{host}:{settings.port}  ({mode})"]
    if generated:
        lines += [
            "[blog] Log in with:",
            f"[blog]     username: {settings.username}",
            f"[blog]     password: {generated}",
            f"[blog] Write it down now: only a hash is stored (in {blog.password_source}), so it cannot be shown again.",
            f"[blog] To choose a different password later, run: {_SET_COMMAND}",
        ]
    elif blog.password_source.startswith("BLOG_PASSWORD"):
        lines.append(f"[blog] Log in as '{settings.username}' with the password from {blog.password_source}.")
    else:
        lines.append(f"[blog] Log in as '{settings.username}'. Forgotten the password? Set a new one with: {_SET_COMMAND}")
    if blog.removed_plaintext_password:
        lines.append(
            "[blog] An earlier version stored your password as plain text. It is now stored as a hash, and the plain-text file was deleted."
        )
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


def set_password(settings: Settings, generate: bool = False, ask=getpass.getpass, out=None) -> int:
    """Store a new password (as a hash). Returns a process exit code."""
    out = out or sys.stderr
    password = passwords.generate_password() if generate else _ask_new_password(ask, out)
    if password is None:
        return 1
    BlogStore(settings.data_dir)  # makes the data folder (owner-only) if this is a brand new blog
    path = passwords.password_file(settings.data_dir)
    passwords.write_hash(path, passwords.hash_password(password))
    (Path(settings.data_dir).expanduser() / passwords.LEGACY_PLAINTEXT_FILE).unlink(missing_ok=True)
    if generate:
        out.write(f"[blog] Your new password is: {password}\n")
        out.write("[blog] Write it down now: only a hash is stored, so it cannot be shown again.\n")
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


def run(settings: Settings, interactive: bool, out=None) -> int:
    """Start the blog. On the very first start, from a terminal, make a password and show it once."""
    out = out or sys.stderr
    generated = None
    try:
        app = create_app(settings)
    except MissingPassword:
        if not interactive:
            out.write("[blog] No login password is set up yet, and this is not an interactive terminal, so none can be shown to you.\n")
            out.write(f"[blog] Run this once in a terminal, then start the blog again: {_SET_COMMAND}\n")
            return 2
        generated = passwords.generate_password()
        passwords.write_hash(passwords.password_file(settings.data_dir), passwords.hash_password(generated))
        app = create_app(settings)
    out.write("\n".join(startup_lines(settings, app.state.blog, generated)) + "\n")
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
    change = commands.add_parser("set-password", help="choose a new login password")
    change.add_argument("--generate", action="store_true", help="generate a random password and show it once")
    change.add_argument("--even-if-redirected", action="store_true",
                        help="print a generated password even when output is not a terminal (it may end up in a log)")
    commands.add_parser("hash-password", help="print a password hash for BLOG_PASSWORD_HASH")
    args = parser.parse_args(argv)
    settings = Settings.from_env()
    if args.command == "set-password":
        if args.generate and not args.even_if_redirected and not sys.stderr.isatty():
            sys.stderr.write(
                "[blog] Refusing to generate a password: output is not a terminal, so it could end up in a log or CI output.\n"
                "[blog] Run this in a terminal, choose one without --generate, or add --even-if-redirected.\n"
            )
            return 2
        return set_password(settings, generate=args.generate)
    if args.command == "hash-password":
        return hash_password_command()
    return run(settings, interactive=sys.stderr.isatty())


if __name__ == "__main__":
    sys.exit(main())
