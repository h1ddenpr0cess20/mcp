import pytest
from unittest.mock import Mock, patch
import requests

from grokipedia_client.client import GrokipediaScraper


class TestGrokipediaScraper:
    """Test cases for the Grokipedia scraper."""

    def test_scrape_sections_success(self, sample_html):
        """Test successful scraping of sections from HTML."""
        with patch("grokipedia_client.client.requests.get") as mock_get:
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
        with patch("grokipedia_client.client.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.text = "<html><body>No content here</body></html>"
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            scraper = GrokipediaScraper()
            sections = scraper.scrape_sections("Empty Page")

            assert sections == []

    def test_scrape_sections_http_error(self):
        """Test error handling for HTTP failures."""
        with patch("grokipedia_client.client.requests.get") as mock_get:
            mock_get.side_effect = Exception("HTTP 404: Not Found")

            scraper = GrokipediaScraper()

            with pytest.raises(Exception, match="HTTP 404: Not Found"):
                scraper.scrape_sections("Nonexistent Page")

    def test_scrape_page_success(self, sample_html):
        """Test successful page scraping with structured return."""
        with patch("grokipedia_client.client.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.text = sample_html
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            scraper = GrokipediaScraper()
            result = scraper.scrape_page("Test Page")

            assert result["page_title"] == "Test Page"
            assert "grokipedia.com/page/Test_Page" in result["url"]
            assert "content" in result
            assert "info_panels" in result
            assert isinstance(result["content"], list)
            assert isinstance(result["info_panels"], list)
            assert len(result["content"]) > 0

    def test_scrape_page_http_error(self):
        """Test scrape_page error handling."""
        with patch("grokipedia_client.client.requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Network error")

            scraper = GrokipediaScraper()
            result = scraper.scrape_page("Test Page")

            assert result["page_title"] == "Test Page"
            assert "grokipedia.com/page/Test_Page" in result["url"]
            assert "error" in result
            assert "Network error" in result["error"]
            assert "content" not in result

    def test_scrape_page_extracts_info_panel(self, sample_html_with_info_panel):
        """Test info panel extraction from aside content."""
        with patch("grokipedia_client.client.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.text = sample_html_with_info_panel
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            scraper = GrokipediaScraper()
            result = scraper.scrape_page("Test Person")

            assert "info_panels" in result
            assert len(result["info_panels"]) == 1

            panel = result["info_panels"][0]
            assert "fields" in panel
            assert panel["fields"][0]["label"] == "Birth Date"
            assert panel["fields"][0]["values"] == ["January 1, 1990"]
            assert panel["fields"][1]["label"] == "Nationality"
            assert panel["fields"][1]["values"] == ["American", "Canadian"]

            assert "image" in panel
            assert panel["image"]["src"] == "https://grokipedia.com/images/test-person.jpg"
            assert panel["image"]["alt"] == "Test person portrait"
            assert panel["image"]["caption"] == "Test person in 2025."

    def test_scrape_sections_excludes_aside_content(self, sample_html_with_info_panel):
        """Test that section content excludes aside info panel fields."""
        with patch("grokipedia_client.client.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.text = sample_html_with_info_panel
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            scraper = GrokipediaScraper()
            sections = scraper.scrape_sections("Test Person")

            assert len(sections) == 2
            all_blocks = [block for section in sections for block in section["blocks"]]
            assert "January 1, 1990" not in all_blocks
            assert "American" not in all_blocks
            assert "Canadian" not in all_blocks

    def test_url_formatting(self):
        """Test that page titles are properly URL-encoded."""
        scraper = GrokipediaScraper()

        # Test spaces converted to underscores
        with patch("grokipedia_client.client.requests.get") as mock_get:
            mock_get.side_effect = Exception("Expected error")
            try:
                scraper.scrape_sections("Test Page")
            except:
                pass

            mock_get.assert_called_once()
            url = mock_get.call_args[0][0]
            assert "Test_Page" in url
            assert "https://grokipedia.com/page/Test_Page" == url

    def test_search_success(self, sample_search_html):
        """Test successful search with results and pagination."""
        with patch("grokipedia_client.client.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.text = sample_search_html
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            scraper = GrokipediaScraper()
            result = scraper.search("python")

            assert result["query"] == "python"
            assert result["page"] == 1
            assert result["total_pages"] == 10
            assert len(result["results"]) == 2

            assert result["results"][0]["title"] == "Python (Efteling)"
            assert result["results"][0]["slug"] == "python_efteling"
            assert result["results"][0]["snippet"] == "Python is a steel roller coaster at Efteling."
            assert result["results"][0]["url"] == "https://grokipedia.com/page/python_efteling"

            assert result["results"][1]["title"] == "Python (programming language)"
            assert result["results"][1]["slug"] == "Python_programming_language"

    def test_search_empty_results(self, sample_search_html_empty):
        """Test search with no matching results."""
        with patch("grokipedia_client.client.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.text = sample_search_html_empty
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            scraper = GrokipediaScraper()
            result = scraper.search("xyznonexistent")

            assert result["query"] == "xyznonexistent"
            assert result["page"] == 1
            assert result["results"] == []
            assert result["total_pages"] == 1

    def test_search_pagination(self, sample_search_html):
        """Test search with explicit page parameter."""
        with patch("grokipedia_client.client.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.text = sample_search_html
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            scraper = GrokipediaScraper()
            result = scraper.search("python", page=3)

            assert result["page"] == 3
            mock_get.assert_called_once_with(
                "https://grokipedia.com/search?q=python&page=3",
                timeout=30,
            )

    def test_search_http_error(self):
        """Test search error handling."""
        with patch("grokipedia_client.client.requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Network error")

            scraper = GrokipediaScraper()
            result = scraper.search("python")

            assert result["query"] == "python"
            assert result["page"] == 1
            assert "error" in result
            assert "Network error" in result["error"]

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

        with patch("grokipedia_client.client.requests.get") as mock_get:
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
