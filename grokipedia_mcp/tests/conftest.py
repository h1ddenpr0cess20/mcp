import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def sample_html():
    """Sample HTML content for Grokipedia testing."""
    return """
    <html>
    <body>
        <article>
            <h1>Test Page</h1>
            <p>This is a test paragraph.</p>
            <h2>Section 1</h2>
            <p>Content for section 1.</p>
            <li>Bullet point 1</li>
            <li>Bullet point 2</li>
            <h3>Subsection</h3>
            <p>More content.</p>
        </article>
    </body>
    </html>
    """


@pytest.fixture
def mock_requests_response(sample_html):
    """Mock response object for requests."""
    mock_response = Mock()
    mock_response.text = sample_html
    mock_response.raise_for_status.return_value = None
    return mock_response


@pytest.fixture
def mock_get_request(mock_requests_response):
    """Mock successful GET request."""
    with patch('grokipedia_client.client.requests.get') as mock_get:
        mock_get.return_value = mock_requests_response
        yield mock_get


@pytest.fixture
def mock_error_response():
    """Mock response that raises an error."""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP 404: Page not found")
    return mock_response


@pytest.fixture
def mock_get_request_error(mock_error_response):
    """Mock GET request that raises an error."""
    with patch('grokipedia_client.client.requests.get') as mock_get:
        mock_get.return_value = mock_error_response
        yield mock_get
