from typing import Optional
from .base import LastfmAPIBase


class AlbumAPI(LastfmAPIBase):
    def add_tags(self, artist: str, album: str, tags: str, sk: Optional[str] = None):
        p = {"artist": artist, "album": album, "tags": tags}
        if sk:
            p["sk"] = sk
        return self._request("album.addtags", p, "POST")

    def get_info(self, artist: Optional[str] = None, album: Optional[str] = None, mbid: Optional[str] = None,
                 autocorrect: Optional[int] = None, username: Optional[str] = None, lang: Optional[str] = None):
        p = {}
        if artist:
            p["artist"] = artist
        if album:
            p["album"] = album
        if mbid:
            p["mbid"] = mbid
        if autocorrect is not None:
            p["autocorrect"] = autocorrect
        if username:
            p["username"] = username
        if lang:
            p["lang"] = lang
        return self._request("album.getinfo", p)

    def get_tags(self, artist: Optional[str] = None, album: Optional[str] = None, mbid: Optional[str] = None,
                 autocorrect: Optional[int] = None, user: Optional[str] = None):
        p = {}
        if artist:
            p["artist"] = artist
        if album:
            p["album"] = album
        if mbid:
            p["mbid"] = mbid
        if autocorrect is not None:
            p["autocorrect"] = autocorrect
        if user:
            p["user"] = user
        return self._request("album.gettags", p)

    def get_top_tags(self, artist: Optional[str] = None, album: Optional[str] = None, mbid: Optional[str] = None,
                     autocorrect: Optional[int] = None):
        p = {}
        if artist:
            p["artist"] = artist
        if album:
            p["album"] = album
        if mbid:
            p["mbid"] = mbid
        if autocorrect is not None:
            p["autocorrect"] = autocorrect
        return self._request("album.gettoptags", p)

    def remove_tag(self, artist: str, album: str, tag: str, sk: Optional[str] = None):
        p = {"artist": artist, "album": album, "tag": tag}
        if sk:
            p["sk"] = sk
        return self._request("album.removetag", p, "POST")

    def search(self, album: str, limit: Optional[int] = None, page: Optional[int] = None):
        p = {"album": album}
        if limit is not None:
            p["limit"] = limit
        if page is not None:
            p["page"] = page
        return self._request("album.search", p)
