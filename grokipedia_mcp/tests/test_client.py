import pytest
from unittest.mock import Mock, patch

from grokipedia_client.client import GrokipediaScraper


class TestGrokipediaScraper:
    """Test cases for the Grokipedia scraper."""

    def test_scrape_sections_success(self, sample_html):
        """Test successful scraping of sections from HTML."""
        with patch('grokipedia_client.client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = sample_html
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            scraper = GrokipediaScraper()
            sections = scraper.scrape_sections("Test Page")

            assert len(sections) == 3  # h1, h2, h3 sections

            # Check h1 section
            assert sections[0]["heading"] == "Test Page"
            assert sections[0]["level"] == 1
            assert "This is a test paragraph" in sections[0]["blocks"][0]

            # Check h2 section
            assert sections[1]["heading"] == "Section 1"
            assert sections[1]["level"] == 2
            assert "Content for section 1" in sections[1]["blocks"][0]
            assert "• Bullet point 1" in sections[1]["blocks"][1]
            assert "• Bullet point 2" in sections[1]["blocks"][2]

            # Check h3 section
            assert sections[2]["heading"] == "Subsection"
            assert sections[2]["level"] == 3
            assert "More content" in sections[2]["blocks"][0]

    def test_scrape_sections_no_content(self):
        """Test scraping with no content found."""
        with patch('grokipedia_client.client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = "<html><body>No content here</body></html>"
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            scraper = GrokipediaScraper()
            sections = scraper.scrape_sections("Empty Page")

            assert sections == []

    def test_scrape_sections_http_error(self):
        """Test error handling for HTTP failures."""
        with patch('grokipedia_client.client.requests.get') as mock_get:
            mock_get.side_effect = Exception("HTTP 404: Not Found")

            scraper = GrokipediaScraper()

            with pytest.raises(Exception, match="HTTP 404: Not Found"):
                scraper.scrape_sections("Nonexistent Page")

    def test_scrape_page_success(self, sample_html):
        """Test successful page scraping with structured return."""
        with patch('grokipedia_client.client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = sample_html
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            scraper = GrokipediaScraper()
            result = scraper.scrape_page("Test Page")

            assert result["page_title"] == "Test Page"
            assert "grokipedia.com/page/Test_Page" in result["url"]
            assert "content" in result
            assert isinstance(result["content"], list)
            assert len(result["content"]) > 0

    def test_scrape_page_http_error(self):
        """Test scrape_page error handling."""
        with patch('grokipedia_client.client.requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")

            scraper = GrokipediaScraper()
            result = scraper.scrape_page("Test Page")

            assert result["page_title"] == "Test Page"
            assert "grokipedia.com/page/Test_Page" in result["url"]
            assert "error" in result
            assert "Network error" in result["error"]
            assert "content" not in result

    def test_url_formatting(self):
        """Test that page titles are properly URL-encoded."""
        scraper = GrokipediaScraper()

        # Test spaces converted to underscores
        with patch('grokipedia_client.client.requests.get') as mock_get:
            mock_get.side_effect = Exception("Expected error")
            try:
                scraper.scrape_sections("Test Page")
            except:
                pass

            mock_get.assert_called_once()
            url = mock_get.call_args[0][0]
            assert "Test_Page" in url
            assert "https://grokipedia.com/page/Test_Page" == url

    def test_parsing_different_html_structures(self):
        """Test parsing with different HTML element structures."""
        test_html = """
        <html>
        <body>
            <div id="content">
                <h2>Main Section</h2>
                <p>Regular paragraph</p>
                <span>Span content</span>
                <ul><li>List item 1</li></ul>
            </div>
        </body>
        </html>
        """

        with patch('grokipedia_client.client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = test_html
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            scraper = GrokipediaScraper()
            sections = scraper.scrape_sections("Test")

            assert len(sections) == 1
            section = sections[0]
            assert section["heading"] == "Main Section"
            assert len(section["blocks"]) == 3  # p, span, li content
