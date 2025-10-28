import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import hashlib

from lastfm_client import (
    LastfmClient, LastfmAPIBase, AlbumAPI, ArtistAPI, AuthAPI, ChartAPI,
    GeoAPI, LibraryAPI, TagAPI, TrackAPI, UserAPI
)


class TestLastfmAPIBase:
    """Test cases for the base Last.fm API class."""

    def test_init_with_api_key_from_env(self):
        """Test initialization with API key from environment variable."""
        with patch.dict(os.environ, {"LASTFM_API_KEY": "test_key"}):
            client = LastfmAPIBase()
            assert client.api_key == "test_key"
            assert client.api_secret == ""
            assert client.session_key == ""

    def test_init_with_explicit_credentials(self):
        """Test initialization with explicit credentials."""
        client = LastfmAPIBase(
            api_key="explicit_key",
            api_secret="explicit_secret",
            session_key="explicit_session"
        )
        assert client.api_key == "explicit_key"
        assert client.api_secret == "explicit_secret"
        assert client.session_key == "explicit_session"

    def test_init_missing_api_key_raises_error(self):
        """Test that missing API key raises RuntimeError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="LASTFM_API_KEY is required"):
                LastfmAPIBase()

    def test_signature_generation(self):
        """Test API signature generation."""
        client = LastfmAPIBase(api_key="test_key", api_secret="test_secret")

        params = {
            "method": "test.method",
            "artist": "Test Artist",
            "track": "Test Track",
            "api_key": "test_key",
            "format": "json"
        }

        # Calculate expected signature
        pieces = []
        for k in sorted(params.keys()):
            if k in {"format", "callback", "api_sig"}:
                continue
            pieces.append(f"{k}{params[k]}")

        raw = "".join(pieces) + "test_secret"
        expected_sig = hashlib.md5(raw.encode("utf-8")).hexdigest()

        actual_sig = client._signature(params)
        assert actual_sig == expected_sig

    @patch('lastfm_client.base.requests.get')
    def test_get_request_success(self, mock_get):
        """Test successful GET request."""
        mock_response = Mock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = LastfmAPIBase(api_key="test_key")
        result = client._request("test.method", {"param": "value"})

        assert result == {"success": True}
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["params"]["method"] == "test.method"
        assert call_args[1]["params"]["api_key"] == "test_key"
        assert call_args[1]["params"]["format"] == "json"

    @patch('lastfm_client.base.requests.post')
    def test_post_request_with_session_key(self, mock_post):
        """Test successful POST request with session key."""
        mock_response = Mock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = LastfmAPIBase(
            api_key="test_key",
            api_secret="test_secret",
            session_key="test_session"
        )

        params = {"artist": "Test Artist", "track": "Test Track"}
        result = client._request("test.method", params, "POST")

        assert result == {"success": True}
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["data"]["sk"] == "test_session"
        assert "api_sig" in call_args[1]["data"]

    def test_post_request_missing_session_key(self):
        """Test POST request without session key raises error."""
        client = LastfmAPIBase(api_key="test_key", api_secret="test_secret")

        with pytest.raises(RuntimeError, match="This method requires a Last.fm session key"):
            client._request("test.method", {"param": "value"}, "POST")

    def test_post_request_missing_api_secret(self):
        """Test POST request without API secret raises error."""
        client = LastfmAPIBase(api_key="test_key", session_key="test_session")

        with pytest.raises(RuntimeError, match="This method requires LASTFM_API_SECRET"):
            client._request("test.method", {"param": "value"}, "POST")

    @patch('lastfm_client.client.requests.get')
    def test_request_raises_for_status(self, mock_get):
        """Test that request properly raises for HTTP errors."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_get.return_value = mock_response

        client = LastfmAPIBase(api_key="test_key")

        with pytest.raises(Exception, match="HTTP Error"):
            client._request("test.method", {"param": "value"})


class TestAlbumAPI:
    """Test cases for the Album API."""

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_add_tags(self, mock_request):
        """Test adding tags to an album."""
        mock_request.return_value = {"status": "ok"}
        api = AlbumAPI(api_key="test_key")

        result = api.add_tags("Test Artist", "Test Album", "rock,pop")

        assert result == {"status": "ok"}
        mock_request.assert_called_once_with(
            "album.addtags",
            {"artist": "Test Artist", "album": "Test Album", "tags": "rock,pop"},
            "POST"
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_info(self, mock_request):
        """Test getting album information."""
        mock_request.return_value = {"album": {"name": "Test Album"}}
        api = AlbumAPI(api_key="test_key")

        result = api.get_info(artist="Test Artist", album="Test Album")

        assert result == {"album": {"name": "Test Album"}}
        mock_request.assert_called_once_with(
            "album.getinfo",
            {"artist": "Test Artist", "album": "Test Album"}
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_tags(self, mock_request):
        """Test getting album tags."""
        mock_request.return_value = {"tags": {"tag": []}}
        api = AlbumAPI(api_key="test_key")

        result = api.get_tags(artist="Test Artist", album="Test Album")

        assert result == {"tags": {"tag": []}}
        mock_request.assert_called_once_with(
            "album.gettags",
            {"artist": "Test Artist", "album": "Test Album"}
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_search(self, mock_request):
        """Test album search."""
        mock_request.return_value = {"results": {"albummatches": {}}}
        api = AlbumAPI(api_key="test_key")

        result = api.search("Test Album", limit=10, page=1)

        assert result == {"results": {"albummatches": {}}}
        mock_request.assert_called_once_with(
            "album.search",
            {"album": "Test Album", "limit": 10, "page": 1}
        )


class TestArtistAPI:
    """Test cases for the Artist API."""

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_info(self, mock_request):
        """Test getting artist information."""
        mock_request.return_value = {"artist": {"name": "Test Artist"}}
        api = ArtistAPI(api_key="test_key")

        result = api.get_info(artist="Test Artist")

        assert result == {"artist": {"name": "Test Artist"}}
        mock_request.assert_called_once_with(
            "artist.getinfo",
            {"artist": "Test Artist"}
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_similar(self, mock_request):
        """Test getting similar artists."""
        mock_request.return_value = {"similarartists": {"artist": []}}
        api = ArtistAPI(api_key="test_key")

        result = api.get_similar(artist="Test Artist", limit=5)

        assert result == {"similarartists": {"artist": []}}
        mock_request.assert_called_once_with(
            "artist.getsimilar",
            {"artist": "Test Artist", "limit": 5}
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_top_albums(self, mock_request):
        """Test getting artist's top albums."""
        mock_request.return_value = {"topalbums": {"album": []}}
        api = ArtistAPI(api_key="test_key")

        result = api.get_top_albums(artist="Test Artist", limit=10)

        assert result == {"topalbums": {"album": []}}
        mock_request.assert_called_once_with(
            "artist.gettopalbums",
            {"artist": "Test Artist", "limit": 10}
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_search(self, mock_request):
        """Test artist search."""
        mock_request.return_value = {"results": {"artistmatches": {}}}
        api = ArtistAPI(api_key="test_key")

        result = api.search("Test Artist", limit=10, page=1)

        assert result == {"results": {"artistmatches": {}}}
        mock_request.assert_called_once_with(
            "artist.search",
            {"artist": "Test Artist", "limit": 10, "page": 1}
        )


class TestAuthAPI:
    """Test cases for the Auth API."""

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_token(self, mock_request):
        """Test getting authentication token."""
        mock_request.return_value = {"token": "test_token_123"}
        api = AuthAPI(api_key="test_key")

        result = api.get_token()

        assert result == {"token": "test_token_123"}
        mock_request.assert_called_once_with("auth.gettoken", {})

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_session(self, mock_request):
        """Test getting session with token."""
        mock_request.return_value = {"session": {"key": "session_123"}}
        api = AuthAPI(api_key="test_key")

        result = api.get_session("test_token_123")

        assert result == {"session": {"key": "session_123"}}
        mock_request.assert_called_once_with(
            "auth.getsession",
            {"token": "test_token_123"},
            "POST"
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_mobile_session(self, mock_request):
        """Test getting mobile session."""
        mock_request.return_value = {"session": {"key": "mobile_session_123"}}
        api = AuthAPI(api_key="test_key")

        result = api.get_mobile_session("testuser", "testpass")

        assert result == {"session": {"key": "mobile_session_123"}}
        mock_request.assert_called_once_with(
            "auth.getmobilesession",
            {"username": "testuser", "password": "testpass"},
            "POST"
        )


class TestChartAPI:
    """Test cases for the Chart API."""

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_top_artists(self, mock_request):
        """Test getting top artists chart."""
        mock_request.return_value = {"artists": {"artist": []}}
        api = ChartAPI(api_key="test_key")

        result = api.get_top_artists(page=1, limit=50)

        assert result == {"artists": {"artist": []}}
        mock_request.assert_called_once_with(
            "chart.gettopartists",
            {"page": 1, "limit": 50}
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_top_tracks(self, mock_request):
        """Test getting top tracks chart."""
        mock_request.return_value = {"tracks": {"track": []}}
        api = ChartAPI(api_key="test_key")

        result = api.get_top_tracks(limit=25)

        assert result == {"tracks": {"track": []}}
        mock_request.assert_called_once_with(
            "chart.gettoptracks",
            {"limit": 25}
        )


class TestTrackAPI:
    """Test cases for the Track API."""

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_info(self, mock_request):
        """Test getting track information."""
        mock_request.return_value = {"track": {"name": "Test Track"}}
        api = TrackAPI(api_key="test_key")

        result = api.get_info(artist="Test Artist", track="Test Track")

        assert result == {"track": {"name": "Test Track"}}
        mock_request.assert_called_once_with(
            "track.getinfo",
            {"artist": "Test Artist", "track": "Test Track"}
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_scrobble(self, mock_request):
        """Test scrobbling a track."""
        mock_request.return_value = {"scrobbles": {"scrobble": {}}}
        api = TrackAPI(api_key="test_key", api_secret="test_secret", session_key="test_session")

        timestamp = 1640995200  # 2022-01-01 00:00:00 UTC
        result = api.scrobble(
            artist="Test Artist",
            track="Test Track",
            timestamp=timestamp,
            album="Test Album"
        )

        assert result == {"scrobbles": {"scrobble": {}}}
        mock_request.assert_called_once_with(
            "track.scrobble",
            {
                "artist": "Test Artist",
                "track": "Test Track",
                "timestamp": timestamp,
                "album": "Test Album"
            },
            "POST"
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_love_track(self, mock_request):
        """Test loving a track."""
        mock_request.return_value = {"status": "ok"}
        api = TrackAPI(api_key="test_key", api_secret="test_secret", session_key="test_session")

        result = api.love("Test Artist", "Test Track")

        assert result == {"status": "ok"}
        mock_request.assert_called_once_with(
            "track.love",
            {"artist": "Test Artist", "track": "Test Track"},
            "POST"
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_search(self, mock_request):
        """Test track search."""
        mock_request.return_value = {"results": {"trackmatches": {}}}
        api = TrackAPI(api_key="test_key")

        result = api.search("Test Track", artist="Test Artist", limit=10)

        assert result == {"results": {"trackmatches": {}}}
        mock_request.assert_called_once_with(
            "track.search",
            {"track": "Test Track", "artist": "Test Artist", "limit": 10}
        )


class TestUserAPI:
    """Test cases for the User API."""

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_info(self, mock_request):
        """Test getting user information."""
        mock_request.return_value = {"user": {"name": "testuser"}}
        api = UserAPI(api_key="test_key")

        result = api.get_info("testuser")

        assert result == {"user": {"name": "testuser"}}
        mock_request.assert_called_once_with(
            "user.getinfo",
            {"user": "testuser"}
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_recent_tracks(self, mock_request):
        """Test getting user's recent tracks."""
        mock_request.return_value = {"recenttracks": {"track": []}}
        api = UserAPI(api_key="test_key")

        result = api.get_recent_tracks("testuser", limit=10)

        assert result == {"recenttracks": {"track": []}}
        mock_request.assert_called_once_with(
            "user.getrecenttracks",
            {"user": "testuser", "limit": 10}
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_top_artists(self, mock_request):
        """Test getting user's top artists."""
        mock_request.return_value = {"topartists": {"artist": []}}
        api = UserAPI(api_key="test_key")

        result = api.get_top_artists("testuser", period="7day", limit=20)

        assert result == {"topartists": {"artist": []}}
        mock_request.assert_called_once_with(
            "user.gettopartists",
            {"user": "testuser", "period": "7day", "limit": 20}
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_loved_tracks(self, mock_request):
        """Test getting user's loved tracks."""
        mock_request.return_value = {"lovedtracks": {"track": []}}
        api = UserAPI(api_key="test_key")

        result = api.get_loved_tracks("testuser", limit=15)

        assert result == {"lovedtracks": {"track": []}}
        mock_request.assert_called_once_with(
            "user.getlovedtracks",
            {"user": "testuser", "limit": 15}
        )


class TestTagAPI:
    """Test cases for the Tag API."""

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_info(self, mock_request):
        """Test getting tag information."""
        mock_request.return_value = {"tag": {"name": "rock"}}
        api = TagAPI(api_key="test_key")

        result = api.get_info("rock")

        assert result == {"tag": {"name": "rock"}}
        mock_request.assert_called_once_with(
            "tag.getinfo",
            {"tag": "rock"}
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_similar(self, mock_request):
        """Test getting similar tags."""
        mock_request.return_value = {"similartags": {"tag": []}}
        api = TagAPI(api_key="test_key")

        result = api.get_similar("rock")

        assert result == {"similartags": {"tag": []}}
        mock_request.assert_called_once_with(
            "tag.getsimilar",
            {"tag": "rock"}
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_top_artists(self, mock_request):
        """Test getting top artists for a tag."""
        mock_request.return_value = {"topartists": {"artist": []}}
        api = TagAPI(api_key="test_key")

        result = api.get_top_artists("rock", limit=25)

        assert result == {"topartists": {"artist": []}}
        mock_request.assert_called_once_with(
            "tag.gettopartists",
            {"tag": "rock", "limit": 25}
        )


class TestGeoAPI:
    """Test cases for the Geo API."""

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_top_artists(self, mock_request):
        """Test getting top artists by country."""
        mock_request.return_value = {"topartists": {"artist": []}}
        api = GeoAPI(api_key="test_key")

        result = api.get_top_artists("United States", limit=30)

        assert result == {"topartists": {"artist": []}}
        mock_request.assert_called_once_with(
            "geo.gettopartists",
            {"country": "United States", "limit": 30}
        )

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_top_tracks(self, mock_request):
        """Test getting top tracks by country and location."""
        mock_request.return_value = {"toptracks": {"track": []}}
        api = GeoAPI(api_key="test_key")

        result = api.get_top_tracks("United Kingdom", location="London", limit=20)

        assert result == {"toptracks": {"track": []}}
        mock_request.assert_called_once_with(
            "geo.gettoptracks",
            {"country": "United Kingdom", "location": "London", "limit": 20}
        )


class TestLibraryAPI:
    """Test cases for the Library API."""

    @patch('lastfm_client.client.LastfmAPIBase._request')
    def test_get_artists(self, mock_request):
        """Test getting user's library artists."""
        mock_request.return_value = {"artists": {"artist": []}}
        api = LibraryAPI(api_key="test_key")

        result = api.get_artists("testuser", limit=40)

        assert result == {"artists": {"artist": []}}
        mock_request.assert_called_once_with(
            "library.getartists",
            {"user": "testuser", "limit": 40}
        )


# Integration test for the complete client
class TestLastfmClientIntegration:
    """Integration tests for the complete Last.fm client."""

    @patch('lastfm_client.client.requests.get')
    def test_end_to_end_request_flow(self, mock_get):
        """Test complete request flow from API call to response."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "artist": {
                "name": "Test Artist",
                "mbid": "test-mbid",
                "stats": {"listeners": "1000", "playcount": "5000"}
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Create client and make request
        client = LastfmAPIBase(api_key="test_key")
        result = client._request("artist.getinfo", {"artist": "Test Artist"})

        # Verify the complete flow
        assert result["artist"]["name"] == "Test Artist"
        assert result["artist"]["mbid"] == "test-mbid"

        # Verify the HTTP request was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args[1]
        assert call_args["params"]["method"] == "artist.getinfo"
        assert call_args["params"]["api_key"] == "test_key"
        assert call_args["params"]["format"] == "json"
        assert call_args["params"]["artist"] == "Test Artist"
