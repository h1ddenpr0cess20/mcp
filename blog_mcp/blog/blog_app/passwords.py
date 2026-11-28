"""Password hashing, and the file that holds the blog's password hash.

The blog never stores the login password. It stores a salted, deliberately slow hash
(PBKDF2-HMAC-SHA256), so a copied data folder or backup does not reveal the password.
Format: ``pbkdf2_sha256$<iterations>$<salt>$<hash>`` with the salt and hash in base64.
"""

import base64
import binascii
import hashlib
import hmac
import os
import secrets
from pathlib import Path

SCHEME = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 600_000  # OWASP's recommended work factor for PBKDF2-HMAC-SHA256
ITERATIONS = DEFAULT_ITERATIONS  # what new hashes use; tests lower it so they do not spend seconds hashing
MAX_ITERATIONS = 50_000_000  # sanity cap for a stored hash, so a corrupted file cannot make a login hang
MIN_LENGTH = 8  # enforced when a person types a new password; generated ones are far longer
SALT_BYTES = 16

HASH_FILE = "password_hash"
LEGACY_PLAINTEXT_FILE = "blog_password"  # written by early versions of the blog; migrated and removed


def hash_password(password: str, iterations: int | None = None, salt: bytes | None = None) -> str:
    """Return the salted hash of a password, ready to store. The salt is random unless one is given."""
    count = iterations or ITERATIONS
    salt = salt or secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, count)
    return f"{SCHEME}${count}${base64.b64encode(salt).decode('ascii')}${base64.b64encode(digest).decode('ascii')}"


def stable_salt(secret_key: str, password: str) -> bytes:
    """A salt derived from this install's secret key, for a password that is hashed afresh at every start.

    Sessions are tied to the hash, so a random salt would sign everyone out on each restart. Deriving it
    keeps the hash stable, while it stays unique to this install and unguessable without the key.
    """
    return hashlib.scrypt(password.encode("utf-8"), salt=b"salt:" + secret_key.encode("utf-8"), n=2**14, r=8, p=1, dklen=SALT_BYTES)


def _parse(encoded: str) -> tuple[int, bytes, bytes] | None:
    parts = str(encoded).strip().split("$")
    if len(parts) != 4 or parts[0] != SCHEME:
        return None
    try:
        iterations = int(parts[1])
        salt = base64.b64decode(parts[2], validate=True)
        digest = base64.b64decode(parts[3], validate=True)
    except (ValueError, binascii.Error):
        return None
    if not 0 < iterations <= MAX_ITERATIONS or not salt or not digest:
        return None
    return iterations, salt, digest


def is_valid_hash(encoded: str) -> bool:
    """True if `encoded` is a well-formed password hash (it says nothing about which password it matches)."""
    return _parse(encoded) is not None


def verify_password(password: str, encoded: str) -> bool:
    """Check a password against a stored hash in constant time. A malformed hash never matches."""
    parsed = _parse(encoded)
    if parsed is None:
        return False
    iterations, salt, digest = parsed
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=len(digest))
    return hmac.compare_digest(candidate, digest)


def generate_password() -> str:
    """A random password: 24 URL-safe characters, about 144 bits."""
    return secrets.token_urlsafe(18)


def password_file(data_dir: Path) -> Path:
    return Path(data_dir) / HASH_FILE


def read_hash(path: Path) -> str | None:
    """The stored hash, or None if there is none (missing or empty file)."""
    try:
        text = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return text or None


def write_hash(path: Path, encoded: str) -> None:
    """Store a hash, readable only by the owner."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(encoded + "\n")
    os.chmod(path, 0o600)


def migrate_legacy_password(data_dir: Path) -> bool:
    """Replace a plaintext password file left by an earlier version with a hash, and delete the plaintext.

    Returns True if there was a plaintext file to remove. An existing hash is never overwritten.
    """
    legacy = Path(data_dir) / LEGACY_PLAINTEXT_FILE
    if not legacy.is_file():
        return False
    plaintext = legacy.read_text(encoding="utf-8").strip()
    target = password_file(data_dir)
    if plaintext and read_hash(target) is None:
        write_hash(target, hash_password(plaintext))
    legacy.unlink()
    return True
