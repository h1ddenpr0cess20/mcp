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
    def __init__(self, api_key: str = None, api_secret: str = None, session_key: str = None):
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
    "UserAPI"
]
