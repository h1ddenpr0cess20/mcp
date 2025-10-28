import os
import pytest
from unittest.mock import Mock, patch

from lastfm_client import (
    LastfmClient, LastfmAPIBase, AlbumAPI, ArtistAPI, AuthAPI, ChartAPI,
    GeoAPI, LibraryAPI, TagAPI, TrackAPI, UserAPI
)


@pytest.fixture
def sample_api_key():
    """Sample API key for testing."""
    return "test_api_key_12345"


@pytest.fixture
def sample_api_secret():
    """Sample API secret for testing."""
    return "test_api_secret_67890"


@pytest.fixture
def sample_session_key():
    """Sample session key for testing."""
    return "test_session_key_abcdef"


@pytest.fixture
def mock_response_data():
    """Sample mock response data for testing."""
    return {
        "artist": {
            "name": "Test Artist",
            "mbid": "test-mbid-123",
            "url": "https://www.last.fm/music/Test+Artist",
            "image": [
                {"#text": "https://example.com/image1.jpg", "size": "small"},
                {"#text": "https://example.com/image2.jpg", "size": "medium"}
            ],
            "stats": {
                "listeners": "1000000",
                "playcount": "50000000"
            },
            "tags": {
                "tag": [
                    {"name": "rock", "url": "https://www.last.fm/tag/rock"},
                    {"name": "alternative", "url": "https://www.last.fm/tag/alternative"}
                ]
            }
        }
    }


@pytest.fixture
def mock_success_response(mock_response_data):
    """Mock response object that returns success data."""
    mock_response = Mock()
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None
    return mock_response


@pytest.fixture
def mock_error_response():
    """Mock response object that raises an HTTP error."""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP 404: Not Found")
    return mock_response


@pytest.fixture
def base_client(sample_api_key):
    """Base Last.fm API client for testing."""
    return LastfmAPIBase(api_key=sample_api_key)


@pytest.fixture
def authenticated_client(sample_api_key, sample_api_secret, sample_session_key):
    """Authenticated Last.fm API client for testing."""
    return LastfmAPIBase(
        api_key=sample_api_key,
        api_secret=sample_api_secret,
        session_key=sample_session_key
    )


@pytest.fixture
def album_api(sample_api_key):
    """Album API client for testing."""
    return AlbumAPI(api_key=sample_api_key)


@pytest.fixture
def artist_api(sample_api_key):
    """Artist API client for testing."""
    return ArtistAPI(api_key=sample_api_key)


@pytest.fixture
def track_api_authenticated(sample_api_key, sample_api_secret, sample_session_key):
    """Authenticated Track API client for testing."""
    return TrackAPI(
        api_key=sample_api_key,
        api_secret=sample_api_secret,
        session_key=sample_session_key
    )


@pytest.fixture
def user_api(sample_api_key):
    """User API client for testing."""
    return UserAPI(api_key=sample_api_key)


@pytest.fixture
def tag_api(sample_api_key):
    """Tag API client for testing."""
    return TagAPI(api_key=sample_api_key)


@pytest.fixture
def chart_api(sample_api_key):
    """Chart API client for testing."""
    return ChartAPI(api_key=sample_api_key)


@pytest.fixture
def geo_api(sample_api_key):
    """Geo API client for testing."""
    return GeoAPI(api_key=sample_api_key)


@pytest.fixture
def library_api(sample_api_key):
    """Library API client for testing."""
    return LibraryAPI(api_key=sample_api_key)


@pytest.fixture
def auth_api(sample_api_key):
    """Auth API client for testing."""
    return AuthAPI(api_key=sample_api_key)


# Environment setup fixtures
@pytest.fixture(autouse=True)
def clean_environment():
    """Clean up environment variables before and after each test."""
    # Store original environment
    original_env = dict(os.environ)

    # Clear Last.fm related environment variables
    lastfm_vars = [k for k in os.environ.keys() if k.startswith('LASTFM_')]
    for var in lastfm_vars:
        del os.environ[var]

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Mock fixtures for HTTP requests
@pytest.fixture
def mock_get_request(mock_success_response):
    """Mock GET request that returns success response."""
    with patch('lastfm_client.base.requests.get') as mock_get:
        mock_get.return_value = mock_success_response
        yield mock_get


@pytest.fixture
def mock_post_request(mock_success_response):
    """Mock POST request that returns success response."""
    with patch('lastfm_client.base.requests.post') as mock_post:
        mock_post.return_value = mock_success_response
        yield mock_post


@pytest.fixture
def mock_get_request_error(mock_error_response):
    """Mock GET request that raises an error."""
    with patch('lastfm_client.base.requests.get') as mock_get:
        mock_get.return_value = mock_error_response
        yield mock_get


@pytest.fixture
def mock_post_request_error(mock_error_response):
    """Mock POST request that raises an error."""
    with patch('lastfm_client.base.requests.post') as mock_post:
        mock_post.return_value = mock_error_response
        yield mock_post
