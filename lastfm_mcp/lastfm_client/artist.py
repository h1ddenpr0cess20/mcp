from typing import Optional
from .base import LastfmAPIBase


class ArtistAPI(LastfmAPIBase):
    def add_tags(self, artist: str, tags: str, sk: Optional[str] = None):
        p = {"artist": artist, "tags": tags}
        if sk:
            p["sk"] = sk
        return self._request("artist.addtags", p, "POST")

    def get_correction(self, artist: str):
        return self._request("artist.getcorrection", {"artist": artist})

    def get_info(self,
                 artist: Optional[str] = None,
                 mbid: Optional[str] = None,
                 lang: Optional[str] = None,
                 autocorrect: Optional[int] = None,
                 username: Optional[str] = None):
        p = {}
        if artist:
            p["artist"] = artist
        if mbid:
            p["mbid"] = mbid
        if lang:
            p["lang"] = lang
        if autocorrect is not None:
            p["autocorrect"] = autocorrect
        if username:
            p["username"] = username
        return self._request("artist.getinfo", p)

    def get_similar(self,
                    artist: Optional[str] = None,
                    mbid: Optional[str] = None,
                    autocorrect: Optional[int] = None,
                    limit: Optional[int] = None):
        p = {}
        if artist:
            p["artist"] = artist
        if mbid:
            p["mbid"] = mbid
        if autocorrect is not None:
            p["autocorrect"] = autocorrect
        if limit is not None:
            p["limit"] = limit
        return self._request("artist.getsimilar", p)

    def get_tags(self,
                 artist: Optional[str] = None,
                 mbid: Optional[str] = None,
                 user: Optional[str] = None,
                 autocorrect: Optional[int] = None):
        p = {}
        if artist:
            p["artist"] = artist
        if mbid:
            p["mbid"] = mbid
        if user:
            p["user"] = user
        if autocorrect is not None:
            p["autocorrect"] = autocorrect
        return self._request("artist.gettags", p)

    def get_top_albums(self,
                       artist: Optional[str] = None,
                       mbid: Optional[str] = None,
                       autocorrect: Optional[int] = None,
                       page: Optional[int] = None,
                       limit: Optional[int] = None):
        p = {}
        if artist:
            p["artist"] = artist
        if mbid:
            p["mbid"] = mbid
        if autocorrect is not None:
            p["autocorrect"] = autocorrect
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("artist.gettopalbums", p)

    def get_top_tags(self,
                     artist: Optional[str] = None,
                     mbid: Optional[str] = None,
                     autocorrect: Optional[int] = None):
        p = {}
        if artist:
            p["artist"] = artist
        if mbid:
            p["mbid"] = mbid
        if autocorrect is not None:
            p["autocorrect"] = autocorrect
        return self._request("artist.gettoptags", p)

    def get_top_tracks(self,
                       artist: Optional[str] = None,
                       mbid: Optional[str] = None,
                       autocorrect: Optional[int] = None,
                       page: Optional[int] = None,
                       limit: Optional[int] = None):
        p = {}
        if artist:
            p["artist"] = artist
        if mbid:
            p["mbid"] = mbid
        if autocorrect is not None:
            p["autocorrect"] = autocorrect
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("artist.gettoptracks", p)

    def remove_tag(self, artist: str, tag: str, sk: Optional[str] = None):
        p = {"artist": artist, "tag": tag}
        if sk:
            p["sk"] = sk
        return self._request("artist.removetag", p, "POST")

    def search(self, artist: str, limit: Optional[int] = None, page: Optional[int] = None):
        p = {"artist": artist}
        if limit is not None:
            p["limit"] = limit
        if page is not None:
            p["page"] = page
        return self._request("artist.search", p)
