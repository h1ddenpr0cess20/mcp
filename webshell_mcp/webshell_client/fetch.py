"""URL content fetching via the VM."""

from __future__ import annotations

import json
from typing import Dict, Optional

from .client import ShellClient

# This script is deployed to the VM and executed remotely.
# It does all the heavy lifting: curl_cffi fetch, trafilatura extraction,
# playwright fallback for JS-rendered pages.
_FETCH_SCRIPT = r'''
import json
import sys
import random

_JS_FALLBACK_THRESHOLD = 512

def _pick_proxy(proxies):
    return random.choice(proxies) if proxies else None

def _extract(html, url, output_format, include_links):
    import trafilatura
    from markdownify import markdownify
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

def _fetch_with_playwright(url, timeout, proxy):
    from playwright.sync_api import sync_playwright
    timeout_ms = int(timeout * 1000)
    launch_kwargs = {"headless": True}
    if proxy:
        launch_kwargs["proxy"] = {"server": proxy}
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            return page.content()
        finally:
            browser.close()

def main():
    args = json.loads(sys.argv[1])
    url = args["url"]
    output_format = args.get("output_format", "markdown")
    include_links = args.get("include_links", True)
    timeout = args.get("timeout", 30.0)
    proxies = args.get("proxies", [])

    from curl_cffi import requests
    proxy = _pick_proxy(proxies)
    resp = requests.get(
        url,
        timeout=timeout,
        impersonate="chrome",
        allow_redirects=True,
        **({"proxy": proxy} if proxy else {}),
    )
    resp.raise_for_status()
    html = resp.text

    result = _extract(html, url, output_format, include_links)

    if len(result["content"]) < _JS_FALLBACK_THRESHOLD:
        try:
            js_html = _fetch_with_playwright(url, timeout, _pick_proxy(proxies))
            js_result = _extract(js_html, url, output_format, include_links)
            if len(js_result["content"]) > len(result["content"]):
                result = js_result
        except Exception:
            pass

    print(json.dumps(result))

if __name__ == "__main__":
    main()
'''

_FETCH_SCRIPT_PATH = ".webshell-mcp/fetch.py"


class FetchClient:
    """Fetch URLs by executing the fetch script on the VM via SSH."""

    def __init__(self, shell: ShellClient, timeout: float = 30.0, proxies: list[str] | None = None):
        self.shell = shell
        self.timeout = timeout
        self.proxies = proxies or []
        self._deployed = False

    def _ensure_deployed(self):
        """Deploy the fetch script to the VM if not already done."""
        if self._deployed:
            return
        self.shell.execute("mkdir -p ~/.webshell-mcp")
        self.shell.write_remote(_FETCH_SCRIPT_PATH, _FETCH_SCRIPT)
        self._deployed = True

    def fetch(
        self,
        url: str,
        *,
        output_format: str = "markdown",
        include_links: bool = True,
    ) -> Dict[str, str]:
        """Fetch a URL on the VM and extract its content.

        Args:
            url: The URL to fetch.
            output_format: "markdown", "text", or "html".
            include_links: Whether to include links in extracted content.

        Returns:
            Dict with keys: url, title, content.
        """
        self._ensure_deployed()
        args = json.dumps({
            "url": url,
            "output_format": output_format,
            "include_links": include_links,
            "timeout": self.timeout,
            "proxies": self.proxies,
        })
        escaped = args.replace("'", "'\\''")
        # Allow extra time for playwright JS rendering fallback
        ssh_timeout = int(self.timeout * 3)
        result = self.shell.execute(f"python3 {_FETCH_SCRIPT_PATH} '{escaped}'", timeout=ssh_timeout)
        if result["exit_code"] != 0:
            return {"url": url, "title": "", "content": f"Error: {result['stderr']}"}
        return json.loads(result["stdout"])
