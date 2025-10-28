from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup


class GrokipediaScraper:
    """
    Scraper for Grokipedia pages using BeautifulSoup.
    """

    def scrape_sections(self, page_title: str) -> List[Dict[str, Any]]:
        """
        Scrape Grokipedia and return a list of sections:
        [
          {"heading": "Early life", "level": 2, "blocks": ["para...", "• bullet ..."]},
          ...
        ]
        """
        url = f"https://grokipedia.com/page/{page_title.replace(' ', '_')}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        content_root = (
            soup.find("article")
            or soup.find("div", {"class": "markdown-body"})
            or soup.find("div", {"id": "content"})
            or soup.body
        )
        if not content_root:
            return []

        allowed = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "ul", "ol", "li"]
        elements = list(content_root.find_all(allowed, recursive=True))

        def start_section(heading_text: Optional[str] = None, level: Optional[int] = None):
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

        return [s for s in sections if s["heading"] is not None or s["blocks"]]

    def scrape_page(self, page_title: str) -> Dict[str, Any]:
        """
        Scrape a Grokipedia page and return structured JSON data.

        Args:
            page_title: The page title (e.g., "Elon Musk").

        Returns:
            dict with keys: page_title, url, content (list of sections).
        """
        url = f"https://grokipedia.com/page/{page_title.replace(' ', '_')}"
        try:
            sections = self.scrape_sections(page_title)
            return {
                "page_title": page_title,
                "url": url,
                "content": sections
            }
        except requests.RequestException as e:
            return {
                "page_title": page_title,
                "url": url,
                "error": f"Failed to fetch page: {e}"
            }
