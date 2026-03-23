"""SearXNG search client."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx


class SearchClient:
    """Client for querying a SearXNG instance."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def search(
        self,
        query: str,
        *,
        categories: Optional[str] = None,
        language: str = "en",
        time_range: Optional[str] = None,
        max_results: int = 10,
        engines: Optional[str] = None,
        safesearch: int = 0,
        pageno: int = 1,
    ) -> List[Dict[str, Any]]:
        """Run a search query against SearXNG.

        Args:
            query: Search query string.
            categories: Comma-separated categories (general, images, news, videos, music, files, it, science, social media, map).
            language: Language code (e.g. "en", "fr", "de").
            time_range: Filter by time (day, week, month, year).
            max_results: Maximum number of results to return.
            engines: Comma-separated engine names to use.
            safesearch: 0=off, 1=moderate, 2=strict.
            pageno: Page number for pagination.

        Returns:
            List of result dicts with keys: title, url, content, engine, score, etc.
        """
        params: Dict[str, Any] = {
            "q": query,
            "format": "json",
            "language": language,
            "safesearch": safesearch,
            "pageno": pageno,
        }
        if categories:
            params["categories"] = categories
        if time_range:
            params["time_range"] = time_range
        if engines:
            params["engines"] = engines

        resp = httpx.get(
            f"{self.base_url}/search",
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        return results[:max_results]
