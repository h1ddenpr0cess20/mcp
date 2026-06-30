from typing import List, Dict, Any, Optional, Tuple
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class GrokipediaScraper:
    """
    Scraper for Grokipedia pages using BeautifulSoup.
    """

    @staticmethod
    def _build_url(page_title: str) -> str:
        return f"https://grokipedia.com/page/{page_title.replace(' ', '_')}"

    def _fetch_soup(
        self,
        page_title: str
    ) -> Tuple[str, BeautifulSoup]:
        url = self._build_url(page_title)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return url, BeautifulSoup(response.text, "html.parser")

    @staticmethod
    def _extract_info_panels(soup: BeautifulSoup) -> List[Dict[str, Any]]:
        panels: List[Dict[str, Any]] = []

        for aside in soup.find_all("aside"):
            dts = aside.find_all("dt")
            if not dts:
                continue

            fields: List[Dict[str, Any]] = []
            for dt in dts:
                dd = dt.find_next_sibling("dd")
                if not dd:
                    continue

                label = dt.get_text(separator=" ", strip=True)
                if not label:
                    continue

                values: List[str] = []
                for node in dd.find_all(["li", "span"]):
                    text = node.get_text(separator=" ", strip=True)
                    if text and text not in values:
                        values.append(text)

                if not values:
                    text = dd.get_text(separator=" ", strip=True)
                    if text:
                        values = [text]

                if values:
                    fields.append({"label": label, "values": values})

            if not fields:
                continue

            panel: Dict[str, Any] = {"fields": fields}
            image = aside.find("img")
            if image:
                src = image.get("src")
                caption = None
                figure = image.find_parent("figure")
                if figure:
                    figcaption = figure.find("figcaption")
                    if figcaption:
                        caption = figcaption.get_text(separator=" ", strip=True) or None

                panel["image"] = {
                    "src": urljoin("https://grokipedia.com", src) if src else None,
                    "alt": image.get("alt"),
                    "caption": caption,
                }

            panels.append(panel)

        return panels

    @staticmethod
    def _extract_sections(soup: BeautifulSoup) -> List[Dict[str, Any]]:
        content_root = (
            soup.find("article")
            or soup.find("div", {"class": "markdown-body"})
            or soup.find("div", {"id": "content"})
            or soup.body
        )
        if not content_root:
            return []

        # Exclude sidebars/info panels from section parsing.
        for aside in content_root.find_all("aside"):
            aside.decompose()

        allowed = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "ul", "ol", "li"]
        elements = list(content_root.find_all(allowed, recursive=True))

        def start_section(
            heading_text: Optional[str] = None,
            level: Optional[int] = None
        ):
            return {"heading": heading_text, "level": level, "blocks": []}

        def push_block(section: Dict[str, Any], text: str):
            t = (text or "").strip()
            if t:
                section["blocks"].append(t)

        sections: List[Dict[str, Any]] = []
        current = start_section()

        for el in elements:
            name = el.name.lower()

            if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                if current["heading"] is not None or current["blocks"]:
                    sections.append(current)
                level = int(name[1])
                heading_text = el.get_text(separator=" ", strip=True) or None
                current = start_section(heading_text, level)
                continue

            if name == "li":
                li_text = el.get_text(separator=" ", strip=True)
                if li_text:
                    push_block(current, f"• {li_text}")
                continue

            if name in ("p", "span"):
                push_block(current, el.get_text(separator=" ", strip=True))
                continue

        if current["heading"] is not None or current["blocks"]:
            sections.append(current)

        non_empty_sections = [s for s in sections if s["heading"] is not None or s["blocks"]]
        if any(s["heading"] is not None for s in non_empty_sections):
            return [s for s in non_empty_sections if s["heading"] is not None]
        return non_empty_sections

    def search(
        self,
        query: str,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Search Grokipedia and return structured results.

        Args:
            query: The search query string.
            page: Page number for pagination (default 1).

        Returns:
            dict with keys: query, page, results (list of dicts with
            title, slug, snippet), total_pages.
        """
        url = f"https://grokipedia.com/search?q={query}&page={page}"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            results: List[Dict[str, str]] = []
            for link in soup.find_all("a", attrs={"data-search-result-link": True}):
                slug = link.get("data-slug", "")
                snippet = link.get("data-search-snippet", "")
                title_span = link.find("span", class_="font-medium")
                title = title_span.get_text(strip=True) if title_span else ""
                if not title:
                    # Fallback: first span with text
                    for span in link.find_all("span"):
                        t = span.get_text(strip=True)
                        if t:
                            title = t
                            break
                if title:
                    results.append({
                        "title": title,
                        "slug": slug,
                        "snippet": snippet,
                        "url": f"https://grokipedia.com/page/{slug}",
                    })

            # Extract total pages from pagination links
            total_pages = page
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if f"q={query}" in href and "&page=" in href:
                    try:
                        p = int(href.split("&page=")[-1])
                        if p > total_pages:
                            total_pages = p
                    except ValueError:
                        pass

            return {
                "query": query,
                "page": page,
                "results": results,
                "total_pages": total_pages,
            }
        except requests.RequestException as e:
            return {
                "query": query,
                "page": page,
                "error": f"Search failed: {e}",
            }

    def scrape_sections(
        self,
        page_title: str
    ) -> List[Dict[str, Any]]:
        """
        Scrape Grokipedia and return a list of sections:
        [
          {"heading": "Early life", "level": 2, "blocks": ["para...", "• bullet ..."]},
          ...
        ]
        """
        _, soup = self._fetch_soup(page_title)
        return self._extract_sections(soup)

    def scrape_page(
        self,
        page_title: str
    ) -> Dict[str, Any]:
        """
        Scrape a Grokipedia page and return structured JSON data.

        Args:
            page_title: The page title (e.g., "Elon Musk").

        Returns:
            dict with keys: page_title, url, content (list of sections),
            info_panels (list of structured panel objects).
        """
        url = self._build_url(page_title)
        try:
            _, soup = self._fetch_soup(page_title)
            info_panels = self._extract_info_panels(soup)
            sections = self._extract_sections(soup)
            return {
                "page_title": page_title,
                "url": url,
                "content": sections,
                "info_panels": info_panels,
            }
        except requests.RequestException as e:
            return {
                "page_title": page_title,
                "url": url,
                "error": f"Failed to fetch page: {e}",
            }
