"""URL content fetching and extraction."""

from __future__ import annotations

import ssl
from typing import Dict

import certifi
import httpx
import trafilatura
from markdownify import markdownify


class FetchClient:
    """Fetch URLs and extract readable content."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        }

    def fetch(
        self,
        url: str,
        *,
        output_format: str = "markdown",
        include_links: bool = True,
    ) -> Dict[str, str]:
        """Fetch a URL and extract its content.

        Args:
            url: The URL to fetch.
            output_format: "markdown", "text", or "html".
            include_links: Whether to include links in extracted content.

        Returns:
            Dict with keys: url, title, content.
        """
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.load_verify_locations(certifi.where())
        resp = httpx.get(
            url,
            timeout=self.timeout,
            headers=self.headers,
            follow_redirects=True,
            verify=ssl_ctx,
        )
        resp.raise_for_status()
        html = resp.text

        title = ""
        content = ""

        if output_format == "html":
            content = html
            doc = trafilatura.bare_extraction(html, url=url)
            if doc:
                title = doc.title or ""
        elif output_format == "text":
            doc = trafilatura.bare_extraction(
                html,
                url=url,
                include_links=include_links,
                output_format="txt",
            )
            if doc:
                title = doc.title or ""
                content = doc.text or ""
        else:
            doc = trafilatura.bare_extraction(
                html,
                url=url,
                include_links=include_links,
            )
            if doc and doc.text:
                title = doc.title or ""
                content = doc.text
            else:
                if doc:
                    title = doc.title or ""
                content = markdownify(html, strip=["img", "script", "style"])

        return {"url": url, "title": title, "content": content}
