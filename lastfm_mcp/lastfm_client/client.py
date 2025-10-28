from .album import AlbumAPI
from .artist import ArtistAPI
from .auth import AuthAPI
from .chart import ChartAPI
from .geo import GeoAPI
from .library import LibraryAPI
from .tag import TagAPI
from .track import TrackAPI
from .user import UserAPI


class LastfmClient:
    """Main client for accessing Last.fm API endpoints.

    This class provides access to various Last.fm APIs through specialized
    sub-clients for albums, artists, authentication, charts, etc.
    """

    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        session_key: str = None
    ):
        """Initialize the Last.fm client.

        Args:
            api_key: Last.fm API key for authentication.
            api_secret: Last.fm API secret for authentication.
            session_key: User session key for authenticated requests.
        """
        self.album = AlbumAPI(api_key, api_secret, session_key)
        self.artist = ArtistAPI(api_key, api_secret, session_key)
        self.auth = AuthAPI(api_key, api_secret, session_key)
        self.chart = ChartAPI(api_key, api_secret, session_key)
        self.geo = GeoAPI(api_key, api_secret, session_key)
        self.library = LibraryAPI(api_key, api_secret, session_key)
        self.tag = TagAPI(api_key, api_secret, session_key)
        self.track = TrackAPI(api_key, api_secret, session_key)
        self.user = UserAPI(api_key, api_secret, session_key)


__all__ = [
    "LastfmClient",
    "AlbumAPI",
    "ArtistAPI",
    "AuthAPI",
    "ChartAPI",
    "GeoAPI",
    "LibraryAPI",
    "TagAPI",
    "TrackAPI",
    "UserAPI",
]
