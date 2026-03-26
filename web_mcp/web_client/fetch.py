"""URL content fetching and extraction."""

from __future__ import annotations

import random
from typing import Dict, List, Optional

import trafilatura
from curl_cffi import requests
from markdownify import markdownify
from playwright.sync_api import sync_playwright


class FetchClient:
    """Fetch URLs and extract readable content."""

    def __init__(self, timeout: float = 30.0, proxies: Optional[List[str]] = None):
        self.timeout = timeout
        self.proxies = proxies or []

    def _pick_proxy(self) -> Optional[str]:
        return random.choice(self.proxies) if self.proxies else None

    def _extract(self, html: str, url: str, output_format: str, include_links: bool) -> Dict[str, str]:
        title = ""
        content = ""
        if output_format == "html":
            content = html
            doc = trafilatura.bare_extraction(html, url=url)
            if doc:
                title = doc.title or ""
        elif output_format == "text":
            doc = trafilatura.bare_extraction(
                html, url=url, include_links=include_links, output_format="txt"
            )
            if doc:
                title = doc.title or ""
                content = doc.text or ""
        else:
            doc = trafilatura.bare_extraction(html, url=url, include_links=include_links)
            if doc and doc.text:
                title = doc.title or ""
                content = doc.text
            else:
                if doc:
                    title = doc.title or ""
                content = markdownify(html, strip=["img", "script", "style"])
        return {"url": url, "title": title, "content": content}

    def fetch(
        self,
        url: str,
        *,
        output_format: str = "markdown",
        include_links: bool = True,
    ) -> Dict[str, str]:
        """Fetch a URL and extract its content using curl.

        Args:
            url: The URL to fetch.
            output_format: "markdown", "text", or "html".
            include_links: Whether to include links in extracted content.

        Returns:
            Dict with keys: url, title, content.
        """
        proxy = self._pick_proxy()
        resp = requests.get(
            url,
            timeout=self.timeout,
            impersonate="chrome",
            allow_redirects=True,
            **({"proxy": proxy} if proxy else {}),
        )
        resp.raise_for_status()
        html = resp.text

        return self._extract(html, url, output_format, include_links)

    def scrape(
        self,
        url: str,
        *,
        output_format: str = "markdown",
        include_links: bool = True,
    ) -> Dict[str, str]:
        """Scrape a URL using a headless Playwright browser.

        Args:
            url: The URL to scrape.
            output_format: "markdown", "text", or "html".
            include_links: Whether to include links in extracted content.

        Returns:
            Dict with keys: url, title, content.
        """
        timeout_ms = int(self.timeout * 1000)
        proxy = self._pick_proxy()
        launch_kwargs = {"headless": True}
        if proxy:
            launch_kwargs["proxy"] = {"server": proxy}
        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_kwargs)
            try:
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                html = page.content()
            finally:
                browser.close()

        return self._extract(html, url, output_format, include_links)
