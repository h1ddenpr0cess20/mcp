"""Markdown rendering and plain-text helpers for blog posts."""

import re

from markdown_it import MarkdownIt

# Raw HTML in a post is escaped rather than passed through, and markdown-it
# refuses javascript:/vbscript:/file: links, so a post can never inject script
# into the viewer even when its text came from an untrusted source.
_md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False}).enable(["table", "strikethrough"])


def _link_open(self, tokens, idx, options, env):
    tokens[idx].attrSet("rel", "noopener noreferrer")
    return self.renderToken(tokens, idx, options, env)


_md.add_render_rule("link_open", _link_open)


def render_markdown(text: str) -> str:
    """Render Markdown to an HTML fragment. Raw HTML in the source is escaped."""
    return _md.render(text or "")


def _inline_text(token) -> str:
    parts = []
    for child in token.children or []:
        if child.type in ("text", "code_inline"):
            parts.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
        elif child.type == "image":
            parts.append(child.content)
    return "".join(parts)


def plain_text(text: str) -> str:
    """Return the readable text of a Markdown document with the syntax removed."""
    parts = []
    for token in _md.parse(text or ""):
        if token.type == "inline":
            parts.append(_inline_text(token))
        elif token.type in ("fence", "code_block"):
            parts.append(token.content)
    return "\n".join(part.strip() for part in parts if part.strip())


def word_count(text: str) -> int:
    """Count the words in a Markdown document, ignoring the syntax."""
    return len(plain_text(text).split())


def make_excerpt(text: str, limit: int = 200) -> str:
    """Build a short plain-text excerpt from the opening paragraphs of a post."""
    tokens = _md.parse(text or "")
    paragraphs = []
    length = 0
    for index, token in enumerate(tokens):
        if token.type == "inline" and index > 0 and tokens[index - 1].type == "paragraph_open":
            paragraph = _inline_text(token).strip()
            if paragraph:
                paragraphs.append(paragraph)
                length += len(paragraph) + 1
                if length >= limit:
                    break
    flat = re.sub(r"\s+", " ", " ".join(paragraphs) or plain_text(text)).strip()
    if len(flat) <= limit:
        return flat
    head = flat[:limit]
    if " " in head:
        head = head.rsplit(" ", 1)[0]
    return head.rstrip(" ,;:.-") + "…"
