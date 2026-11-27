"""Blog settings, read from the environment, plus the secrets the blog keeps on disk."""

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


def load_or_create_secret(path: Path, nbytes: int = 24) -> str:
    """Return the secret stored at `path`, creating it (owner-only) on first use."""
    try:
        existing = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        existing = ""
    if existing:
        return existing
    value = secrets.token_urlsafe(nbytes)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(value + "\n")
    os.chmod(path, 0o600)
    return value


def _flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    data_dir: Path
    host: str = "127.0.0.1"
    port: int = 9901
    title: str = "Private Blog"
    description: str = ""
    username: str = "owner"
    password: str = ""  # plaintext, from BLOG_PASSWORD; hashed in memory at startup and never written anywhere
    password_hash: str = ""  # from BLOG_PASSWORD_HASH: a hash made by `blog.py hash-password`; wins over `password`
    public: bool = False  # True: published posts are readable without logging in
    public_url: str = ""  # absolute address used in links returned by the API; default: taken from the request
    api_token: str = ""  # empty: generated into data_dir/api_token
    max_attachment_mb: int = 25  # largest file that can be attached to a post
    tls_cert: str = ""
    tls_key: str = ""

    def __post_init__(self):
        self.data_dir = Path(os.path.expanduser(str(self.data_dir)))
        if not self.username or ":" in self.username:
            raise ValueError("BLOG_USERNAME must be non-empty and must not contain ':'")
        self.tls_cert = os.path.expanduser(self.tls_cert)
        self.tls_key = os.path.expanduser(self.tls_key)
        if bool(self.tls_cert) != bool(self.tls_key):
            raise ValueError("BLOG_TLS_CERT and BLOG_TLS_KEY must be set together")
        self.public_url = self.public_url.rstrip("/")
        if not 1 <= self.max_attachment_mb <= 2048:
            raise ValueError("BLOG_MAX_ATTACHMENT_MB must be between 1 and 2048")

    @property
    def max_attachment_bytes(self) -> int:
        return self.max_attachment_mb * 1024 * 1024

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("BLOG_DIR", "~/mcp-blog")),
            host=os.getenv("BLOG_HOST", "127.0.0.1"),
            port=int(os.getenv("BLOG_PORT", "9901")),
            title=os.getenv("BLOG_TITLE", "Private Blog"),
            description=os.getenv("BLOG_DESCRIPTION", ""),
            username=os.getenv("BLOG_USERNAME", "owner"),
            password=os.getenv("BLOG_PASSWORD", ""),
            password_hash=os.getenv("BLOG_PASSWORD_HASH", ""),
            public=_flag("BLOG_PUBLIC"),
            public_url=os.getenv("BLOG_PUBLIC_URL", ""),
            api_token=os.getenv("BLOG_API_TOKEN", ""),
            max_attachment_mb=int(os.getenv("BLOG_MAX_ATTACHMENT_MB", "25")),
            tls_cert=os.getenv("BLOG_TLS_CERT", ""),
            tls_key=os.getenv("BLOG_TLS_KEY", ""),
        )
