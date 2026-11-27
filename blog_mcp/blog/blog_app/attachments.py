"""Files attached to posts: cleaning names, detecting text, and storing the bytes safely.

An attachment is untrusted data. The blog never opens, runs, or renders one: it is stored under a
random name with no extension, and only ever offered for download (or shown as escaped text).
"""

import hashlib
import mimetypes
import os
import re
import tempfile
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .store import NotFound, TooLarge

MAX_FILENAME_CHARS = 150
PREVIEW_BYTES = 512 * 1024  # text files up to this size can be read in the browser
CHUNK_BYTES = 1024 * 1024
SNIFF_BYTES = 64 * 1024  # how much of a file is examined to decide whether it is text
STALE_PARTIAL_SECONDS = 3600

_ID = re.compile(r"^[0-9a-f]{32}$")
_CONTENT_TYPE = re.compile(r"^[\w.+-]+/[\w.+-]+$")
# Characters that are invisible or reorder the text around them, so "invoice‮gpj.exe" cannot pass for a picture.
_INVISIBLE = dict.fromkeys(map(ord, "­​‌‍‎‏  ‪‫‬‭‮⁦⁧⁨⁩﻿"), None)


def clean_filename(name: str) -> str:
    """Make an uploaded file's name safe to show and to put in a download header.

    Drops any folder part, control and invisible characters, and over-long names. It is only ever a label:
    the file is stored under a random name, so this never decides where anything is written.
    """
    text = unicodedata.normalize("NFC", str(name or "")).replace("\\", "/").rsplit("/", 1)[-1].translate(_INVISIBLE)
    text = re.sub(r"\s+", " ", "".join(ch for ch in text if ch.isprintable())).strip()
    if text in ("", ".", ".."):
        return "file"
    if len(text) > MAX_FILENAME_CHARS:
        stem, extension = os.path.splitext(text)
        extension = extension[:20]
        text = stem[: MAX_FILENAME_CHARS - len(extension)] + extension
    return text


def guess_content_type(filename: str) -> str:
    """A label from the file's extension, for display only. It is never used to decide how a file is served."""
    guessed = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return guessed if _CONTENT_TYPE.match(guessed) else "application/octet-stream"


def looks_like_text(head: bytes) -> bool:
    """True if the start of a file is UTF-8 text (so it can be read in the browser)."""
    if b"\x00" in head:
        return False
    try:
        head.decode("utf-8")
    except UnicodeDecodeError as error:
        return error.reason == "unexpected end of data" and error.start >= len(head) - 3  # cut off mid-character
    return True


@dataclass
class Received:
    """An upload that has been read to a temporary file but not yet attached."""

    path: Path
    size: int
    sha256: str
    is_text: bool


class AttachmentFiles:
    """Where attachment bytes live: one owner-only file per attachment, named by its random id."""

    def __init__(self, directory: Path, max_bytes: int):
        self.directory = Path(directory)
        self.max_bytes = max_bytes
        self._sweep_partial_uploads()

    def _sweep_partial_uploads(self) -> None:
        """Delete half-written uploads left behind by a crash."""
        if self.directory.is_dir():
            for partial in self.directory.glob(".incoming-*"):
                if time.time() - partial.stat().st_mtime > STALE_PARTIAL_SECONDS:
                    partial.unlink(missing_ok=True)

    def path(self, attachment_id: str) -> Path:
        if not _ID.fullmatch(attachment_id):  # fullmatch: `$` would also accept a trailing newline
            raise NotFound("Attachment not found")
        return self.directory / attachment_id

    async def receive(self, upload) -> Received:
        """Read an uploaded file to a temporary file, enforcing the size limit while it streams in.

        `upload` is anything with an async `read(size)`. A file that is too large is stopped as soon as it
        passes the limit, so it never has to be held in memory or fully written to disk.
        """
        self.directory.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=self.directory, prefix=".incoming-")  # created owner-only
        digest, size, head = hashlib.sha256(), 0, b""
        try:
            with os.fdopen(descriptor, "wb") as out:
                while chunk := await upload.read(CHUNK_BYTES):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise TooLarge(f"Files can be at most {self.max_bytes // (1024 * 1024)} MB")
                    if len(head) < SNIFF_BYTES:
                        head += chunk[: SNIFF_BYTES - len(head)]
                    digest.update(chunk)
                    out.write(chunk)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
        return Received(Path(temporary), size, digest.hexdigest(), looks_like_text(head))

    def commit(self, received: Received, attachment_id: str) -> None:
        """Move a received file into place under its id, replacing any earlier file with that id."""
        os.chmod(received.path, 0o600)
        os.replace(received.path, self.path(attachment_id))

    @staticmethod
    def discard(received: Received) -> None:
        received.path.unlink(missing_ok=True)

    def remove(self, attachment_id: str) -> None:
        self.path(attachment_id).unlink(missing_ok=True)

    def read_text(self, attachment_id: str, limit: int = PREVIEW_BYTES) -> tuple[str, bool]:
        """The start of a text file as a string, and whether it was cut short."""
        with open(self.path(attachment_id), "rb") as handle:
            data = handle.read(limit + 1)
        return data[:limit].decode("utf-8", errors="replace"), len(data) > limit


__all__ = ["AttachmentFiles", "Received", "clean_filename", "guess_content_type", "looks_like_text"]
