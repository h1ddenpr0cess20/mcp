"""Tests for Markdown rendering and the plain-text helpers."""

import pytest

from blog_app.render import make_excerpt, plain_text, render_markdown, word_count


class TestRenderMarkdown:
    @pytest.mark.unit
    def test_basic_markup(self):
        html = render_markdown("# Title\n\nSome **bold** and *italic* text.")
        assert "<h1>Title</h1>" in html
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html

    @pytest.mark.unit
    def test_raw_html_is_escaped(self):
        html = render_markdown("<script>alert(1)</script>\n\nInline <b>bold</b> and <img src=x onerror=alert(1)>")
        assert "<script>" not in html
        assert "<b>" not in html
        assert "<img src=x" not in html
        assert "&lt;script&gt;" in html

    @pytest.mark.unit
    @pytest.mark.parametrize("url", [
        "javascript:alert(1)",
        "JaVaScRiPt:alert(1)",
        "vbscript:msgbox(1)",
        "data:text/html,<script>1</script>",
    ])
    def test_dangerous_link_schemes_are_not_linked(self, url):
        html = render_markdown(f"[click]({url})")
        assert "<a " not in html
        assert 'href="' + url not in html

    @pytest.mark.unit
    def test_safe_links_get_rel_noopener(self):
        html = render_markdown("[ok](https://example.com/page)")
        assert 'href="https://example.com/page"' in html
        assert 'rel="noopener noreferrer"' in html

    @pytest.mark.unit
    def test_tables_and_strikethrough(self):
        html = render_markdown("| a | b |\n|---|---|\n| 1 | 2 |\n\n~~gone~~")
        assert "<table>" in html
        assert "<s>gone</s>" in html

    @pytest.mark.unit
    def test_code_block_content_is_escaped(self):
        html = render_markdown("```\n<div>&</div>\n```")
        assert "&lt;div&gt;&amp;&lt;/div&gt;" in html

    @pytest.mark.unit
    def test_empty_input(self):
        assert render_markdown("") == ""
        assert render_markdown(None) == ""


class TestPlainText:
    @pytest.mark.unit
    def test_strips_syntax(self):
        text = plain_text("# Heading\n\nA **bold** [link](https://example.com) and `code`.")
        assert text == "Heading\nA bold link and code."

    @pytest.mark.unit
    def test_includes_code_blocks_and_image_alt_text(self):
        text = plain_text("![a diagram](x.png)\n\n```\nprint('hi')\n```")
        assert "a diagram" in text
        assert "print('hi')" in text

    @pytest.mark.unit
    def test_word_count(self):
        assert word_count("# Two words\n\nthree more words") == 5
        assert word_count("") == 0
        assert word_count("**bold** `code`") == 2


class TestMakeExcerpt:
    @pytest.mark.unit
    def test_uses_first_paragraph_not_heading(self):
        assert make_excerpt("# Big Title\n\nThe opening paragraph.\n\nSecond.") == "The opening paragraph. Second."

    @pytest.mark.unit
    def test_truncates_at_word_boundary_with_ellipsis(self):
        excerpt = make_excerpt("word " * 100, limit=50)
        assert excerpt.endswith("…")
        assert len(excerpt) <= 51
        assert "wor…" not in excerpt

    @pytest.mark.unit
    def test_short_text_is_returned_whole(self):
        assert make_excerpt("Short post.") == "Short post."

    @pytest.mark.unit
    def test_falls_back_to_plain_text_when_no_paragraphs(self):
        assert make_excerpt("# Only a heading") == "Only a heading"

    @pytest.mark.unit
    def test_ignores_list_items_quotes_code_and_tables(self):
        text = ("Opening paragraph.\n\n## Heading\n\n- first item\n- second item\n\n> a quoted line\n\n"
                "```\ncode here\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
        assert make_excerpt(text) == "Opening paragraph."

    @pytest.mark.unit
    def test_does_not_borrow_a_list_when_the_post_starts_with_one(self):
        assert make_excerpt("- only a list\n- of items") == "only a list of items"  # falls back to the plain text

    @pytest.mark.unit
    def test_empty(self):
        assert make_excerpt("") == ""

    @pytest.mark.unit
    def test_collapses_whitespace_and_line_breaks(self):
        assert make_excerpt("line one\nline two   spaced") == "line one line two spaced"
