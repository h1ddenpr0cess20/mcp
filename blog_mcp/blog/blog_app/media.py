"""Image uploads: validate by content, store under unguessable names, serve safely."""

import re
import secrets
from pathlib import Path

from .store import BlogError

MAX_IMAGE_BYTES = 8 * 1024 * 1024

MEDIA_TYPES = {"png": "image/png", "jpg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}
NAME_PATTERN = re.compile(r"^[0-9a-f]{32}\.(png|jpg|gif|webp)$")


def detect_image_type(data: bytes) -> str | None:
    """Identify an image from its first bytes (never from a client-supplied name or type). SVG is deliberately not accepted."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def save_image(media_dir: Path, data: bytes) -> str:
    """Store an uploaded image and return its file name. Raises BlogError for anything that is not a PNG, JPEG, GIF, or WebP."""
    if not data:
        raise BlogError("The uploaded file is empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise BlogError(f"Images can be at most {MAX_IMAGE_BYTES // (1024 * 1024)} MB")
    kind = detect_image_type(data)
    if kind is None:
        raise BlogError("Only PNG, JPEG, GIF, and WebP images can be uploaded")
    media_dir.mkdir(parents=True, exist_ok=True)
    name = f"{secrets.token_hex(16)}.{kind}"
    (media_dir / name).write_bytes(data)
    return name


def media_path(media_dir: Path, name: str) -> Path | None:
    """The file for a media name, or None if the name is not one we generate or the file is missing."""
    if not NAME_PATTERN.fullmatch(name):  # fullmatch: `$` would also accept a trailing newline
        return None
    path = media_dir / name
    return path if path.is_file() else None
