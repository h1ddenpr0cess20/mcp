"""Login sessions, CSRF tokens, login throttling, and API-token checks.

Everything here is stdlib. Sessions are HMAC-signed cookies that expire, carry a
per-session CSRF token, and stop working if the blog's password changes.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Callable

from .passwords import verify_password

SESSION_COOKIE = "blog_session"
SESSION_SECONDS = 14 * 24 * 3600


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _same(a: str, b: str) -> bool:
    return hmac.compare_digest(str(a).encode("utf-8"), str(b).encode("utf-8"))


class Auth:
    """Checks credentials and issues/reads session cookies and API tokens."""

    def __init__(self, username: str, password_hash: str, secret_key: str, api_token: str):
        self.username = username
        self._password_hash = password_hash  # the password itself is never held
        self._key = secret_key.encode("utf-8")
        self._api_token = api_token
        # Setting a new password changes this value, which signs every existing session out.
        self._fingerprint = hmac.new(self._key, password_hash.encode("utf-8"), hashlib.sha256).hexdigest()[:16]

    # --- password login ----------------------------------------------------

    def check_login(self, username: str, password: str) -> bool:
        """Check both fields without short-circuiting, so a wrong username takes as long as a wrong password."""
        user_ok = _same(username, self.username)
        password_ok = verify_password(password, self._password_hash)
        return user_ok and password_ok

    # --- sessions ----------------------------------------------------------

    def _sign(self, raw: str) -> str:
        return _b64(hmac.new(self._key, raw.encode("ascii"), hashlib.sha256).digest())

    def new_session(self) -> tuple[str, dict]:
        """Return (cookie value, session data) for a fresh login."""
        data = {"u": self.username, "csrf": secrets.token_urlsafe(24), "exp": int(time.time()) + SESSION_SECONDS, "v": self._fingerprint}
        raw = _b64(json.dumps(data, separators=(",", ":")).encode("utf-8"))
        return f"{raw}.{self._sign(raw)}", data

    def read_session(self, cookie: str | None) -> dict | None:
        """Return the session data for a valid, unexpired cookie, else None."""
        if not cookie or "." not in cookie:
            return None
        raw, _, signature = cookie.partition(".")
        try:
            if not _same(signature, self._sign(raw)):
                return None
            data = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
        except (ValueError, TypeError, UnicodeError):
            return None
        if not isinstance(data, dict) or data.get("exp", 0) < time.time():
            return None
        if data.get("u") != self.username or not _same(str(data.get("v", "")), self._fingerprint):
            return None
        return data

    @staticmethod
    def check_csrf(session: dict | None, supplied: str | None) -> bool:
        return bool(session and supplied and _same(session["csrf"], supplied))

    # --- API token ---------------------------------------------------------

    def check_api_token(self, header: str | None) -> bool:
        """Check an `Authorization: Bearer <token>` header."""
        if not header or header[:7].lower() != "bearer ":
            return False
        return _same(header[7:].strip(), self._api_token)


class LoginThrottle:
    """Blocks a client after too many failed logins within a time window."""

    def __init__(self, max_failures: int = 5, window: float = 900.0, clock: Callable[[], float] = time.monotonic):
        self.max_failures = max_failures
        self.window = window
        self._clock = clock
        self._failures: dict[str, list[float]] = {}

    def _recent(self, key: str) -> list[float]:
        cutoff = self._clock() - self.window
        recent = [t for t in self._failures.get(key, []) if t > cutoff]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def retry_after(self, key: str) -> int:
        """Seconds until this client may try again; 0 if it may try now."""
        recent = self._recent(key)
        if len(recent) < self.max_failures:
            return 0
        return max(1, int(recent[0] + self.window - self._clock()) + 1)

    def record_failure(self, key: str) -> None:
        if len(self._failures) > 10_000:  # a flood of distinct clients must not grow memory forever
            for stale in list(self._failures):
                self._recent(stale)
        self._failures.setdefault(key, []).append(self._clock())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
