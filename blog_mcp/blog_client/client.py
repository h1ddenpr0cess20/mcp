import os
from pathlib import Path
from urllib.parse import quote

import requests
from fastmcp.exceptions import ToolError

MAX_IMAGE_BYTES = 8 * 1024 * 1024


class BlogError(ToolError):
    """The blog refused a request or could not be used. A ToolError, so FastMCP reports the message
    to the model as a normal tool failure and logs one line instead of a traceback."""


class BlogUnreachable(BlogError):
    """The blog could not be contacted at all (not running, wrong address, timeout, bad certificate)."""


class BlogClient:
    """Client for the blog's JSON API (/api/v1). The blog is a separate program; this only talks to it."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float | None = None,
        verify_tls: bool | None = None,
        session: requests.Session | None = None,
    ):
        """Initialize the client.

        Args:
            base_url: Blog address. If None, reads BLOG_URL (default http://127.0.0.1:9901).
            token: API token. If None, reads BLOG_API_TOKEN, then the api_token file in BLOG_DIR.
            timeout: Request timeout in seconds. If None, reads BLOG_TIMEOUT (default 30).
            verify_tls: Verify HTTPS certificates. If None, reads BLOG_VERIFY_TLS (default true).
            session: A requests session to use (for tests).
        """
        self.base_url = (base_url or os.getenv("BLOG_URL", "http://127.0.0.1:9901")).rstrip("/")
        self.token = token or os.getenv("BLOG_API_TOKEN", "") or self._token_from_file()
        self.timeout = timeout if timeout is not None else float(os.getenv("BLOG_TIMEOUT", "30"))
        if verify_tls is None:
            verify_tls = os.getenv("BLOG_VERIFY_TLS", "true").strip().lower() not in ("0", "false", "no", "off")
        self.verify_tls = verify_tls
        self._session = session or requests.Session()

    @staticmethod
    def _token_from_file() -> str:
        """The token the blog generated, when it runs on this machine with the default storage location."""
        path = Path(os.path.expanduser(os.getenv("BLOG_DIR", "~/mcp-blog"))) / "api_token"
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    # --- transport ---------------------------------------------------------

    def _request(self, method: str, path: str, *, params: dict | None = None, json: dict | None = None, files: dict | None = None):
        if not self.token:
            raise BlogError(
                "No blog API token is configured. Set BLOG_API_TOKEN, or run the blog on this machine so its "
                "api_token file can be found (see BLOG_DIR)."
            )
        try:
            response = self._session.request(
                method, f"{self.base_url}{path}", params=params, json=json, files=files,
                headers={"Authorization": f"Bearer {self.token}"}, timeout=self.timeout,
                verify=self.verify_tls,
                allow_redirects=False,  # never forward the token to wherever a redirect points
            )
        except requests.exceptions.SSLError:
            raise BlogUnreachable(
                f"TLS verification failed for {self.base_url}. For a self-signed certificate set BLOG_VERIFY_TLS=false."
            ) from None
        except requests.exceptions.Timeout:
            raise BlogUnreachable(f"The blog at {self.base_url} did not answer within {self.timeout:g} seconds.") from None
        except requests.exceptions.RequestException:
            raise BlogUnreachable(
                f"Cannot reach the blog at {self.base_url}. Is it running? Start it with `python blog/blog.py`, "
                "or fix BLOG_URL."
            ) from None
        if 300 <= response.status_code < 400:
            raise BlogError(
                f"The blog at {self.base_url} redirected the request. Point BLOG_URL at its final address (for example the https:// one)."
            )
        try:
            data = response.json()
        except ValueError:
            raise BlogError(f"Unexpected response from {self.base_url} (HTTP {response.status_code}). Is BLOG_URL the blog?") from None
        if response.status_code == 401:
            raise BlogError("The blog rejected the API token. Check BLOG_API_TOKEN against the blog's api_token.")
        if response.status_code >= 400:
            message = data.get("error") if isinstance(data, dict) else None
            raise BlogError(message or f"The blog returned an error (HTTP {response.status_code}).")
        return data

    # --- posts -------------------------------------------------------------

    def create_post(self, title: str, body: str = "", tags: list[str] | None = None, slug: str = "", summary: str = "",
                    publish: bool = False) -> dict:
        """Create a post. Drafts are the default."""
        payload = {"title": title, "body": body, "tags": tags or [], "slug": slug, "summary": summary, "publish": publish}
        return self._request("POST", "/api/v1/posts", json=payload)

    def get_post(self, slug: str) -> dict:
        """Fetch one post, including its Markdown body."""
        return self._request("GET", f"/api/v1/posts/{self._slug(slug)}")

    def list_posts(self, status: str = "all", tag: str = "", limit: int = 20, offset: int = 0) -> dict:
        """List posts without their bodies, newest first."""
        return self._request("GET", "/api/v1/posts", params={"status": status, "tag": tag, "limit": limit, "offset": offset})

    def update_post(self, slug: str, title: str | None = None, body: str | None = None, summary: str | None = None,
                    tags: list[str] | None = None, new_slug: str | None = None) -> dict:
        """Change a post. A field left as None is not sent, so it is not touched."""
        changes = {"title": title, "body": body, "summary": summary, "tags": tags, "slug": new_slug}
        return self._request("PATCH", f"/api/v1/posts/{self._slug(slug)}", json={k: v for k, v in changes.items() if v is not None})

    def replace_in_post(self, slug: str, find: str, replace: str, replace_all: bool = False) -> dict:
        """Find and replace text in a post's body."""
        return self._request("POST", f"/api/v1/posts/{self._slug(slug)}/replace",
                             json={"find": find, "replace": replace, "replace_all": replace_all})

    def set_status(self, slug: str, status: str) -> dict:
        """Publish a post, or return it to draft."""
        if status not in ("published", "draft"):
            raise BlogError("status must be 'draft' or 'published'")
        action = "publish" if status == "published" else "unpublish"
        return self._request("POST", f"/api/v1/posts/{self._slug(slug)}/{action}")

    def delete_post(self, slug: str) -> bool:
        """Permanently delete a post. Returns False if it did not exist."""
        try:
            self._request("DELETE", f"/api/v1/posts/{self._slug(slug)}")
        except BlogError as exc:
            if "not found" in str(exc).lower() and not isinstance(exc, BlogUnreachable):
                return False
            raise
        return True

    # --- discovery ---------------------------------------------------------

    def search_posts(self, query: str, status: str = "all", limit: int = 20) -> dict:
        """Search titles, summaries, bodies, and tags."""
        return self._request("GET", "/api/v1/search", params={"q": query, "status": status, "limit": limit})

    def list_tags(self, status: str = "all") -> dict:
        """List every tag with its post count."""
        return self._request("GET", "/api/v1/tags", params={"status": status})

    def info(self) -> dict:
        """The blog's title, address, mode, and post counts."""
        return self._request("GET", "/api/v1/info")

    # --- images ------------------------------------------------------------

    def upload_image(self, file_path: str) -> dict:
        """Upload a local image file to the blog. Returns its address on the blog."""
        path = Path(os.path.expanduser(file_path))
        if not path.is_file():
            raise BlogError(f"No file at {file_path}")
        if path.stat().st_size > MAX_IMAGE_BYTES:
            raise BlogError(f"Images can be at most {MAX_IMAGE_BYTES // (1024 * 1024)} MB")
        with path.open("rb") as handle:
            return self._request("POST", "/api/v1/media", files={"file": (path.name, handle)})

    @staticmethod
    def _slug(slug: str) -> str:
        """Percent-encode a slug for use in a URL path, so it can never alter the path."""
        return quote(str(slug), safe="")
