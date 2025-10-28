
import hashlib
import os
from typing import Any, Dict, Optional

import requests

BASE_URL = "https://ws.audioscrobbler.com/2.0/"

class LastfmAPIBase:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, session_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LASTFM_API_KEY", "")
        self.api_secret = api_secret or os.getenv("LASTFM_API_SECRET", "")
        self.session_key = session_key or os.getenv("LASTFM_SESSION_KEY", "")

        if not self.api_key:
            raise RuntimeError("LASTFM_API_KEY is required")

    def _signature(self, params: Dict[str, Any]) -> str:
        # Build api_sig per Last.fm: sort keys, concat key+value, append secret, md5
        pieces = []
        for k in sorted(params.keys()):
            if k in {"format", "callback", "api_sig"}:
                continue
            pieces.append(f"{k}{params[k]}")
        raw = "".join(pieces) + self.api_secret
        import hashlib as _h
        return _h.md5(raw.encode("utf-8")).hexdigest()

    def _request(self, method: str, params: Dict[str, Any], http_method: str = "GET"):
        params = {**params}
        params["api_key"] = self.api_key
        params["format"] = "json"
        params["method"] = method

        if http_method == "POST":
            # need session key + signature
            if not params.get("sk"):
                if not self.session_key:
                    raise RuntimeError("This method requires a Last.fm session key. Provide LASTFM_SESSION_KEY or pass sk.")
                params["sk"] = self.session_key
            if not self.api_secret:
                raise RuntimeError("This method requires LASTFM_API_SECRET for signing.")
            params["api_sig"] = self._signature(params)
            r = requests.post(BASE_URL, data=params, timeout=30)
        else:
            r = requests.get(BASE_URL, params=params, timeout=30)

        r.raise_for_status()
        return r.json()

# ---------- Album ----------
class AlbumAPI(LastfmAPIBase):
    def add_tags(self, artist: str, album: str, tags: str, sk: Optional[str] = None):
        p = {"artist": artist, "album": album, "tags": tags}
        if sk: p["sk"] = sk
        return self._request("album.addtags", p, "POST")

    def get_info(self, artist: Optional[str] = None, album: Optional[str] = None, mbid: Optional[str] = None,
                 autocorrect: Optional[int] = None, username: Optional[str] = None, lang: Optional[str] = None):
        p = {}
        if artist: p["artist"] = artist
        if album: p["album"] = album
        if mbid: p["mbid"] = mbid
        if autocorrect is not None: p["autocorrect"] = autocorrect
        if username: p["username"] = username
        if lang: p["lang"] = lang
        return self._request("album.getinfo", p)

    def get_tags(self, artist: Optional[str] = None, album: Optional[str] = None, mbid: Optional[str] = None,
                 autocorrect: Optional[int] = None, user: Optional[str] = None):
        p = {}
        if artist: p["artist"] = artist
        if album: p["album"] = album
        if mbid: p["mbid"] = mbid
        if autocorrect is not None: p["autocorrect"] = autocorrect
        if user: p["user"] = user
        return self._request("album.gettags", p)

    def get_top_tags(self, artist: Optional[str] = None, album: Optional[str] = None, mbid: Optional[str] = None,
                     autocorrect: Optional[int] = None):
        p = {}
        if artist: p["artist"] = artist
        if album: p["album"] = album
        if mbid: p["mbid"] = mbid
        if autocorrect is not None: p["autocorrect"] = autocorrect
        return self._request("album.gettoptags", p)

    def remove_tag(self, artist: str, album: str, tag: str, sk: Optional[str] = None):
        p = {"artist": artist, "album": album, "tag": tag}
        if sk: p["sk"] = sk
        return self._request("album.removetag", p, "POST")

    def search(self, album: str, limit: Optional[int] = None, page: Optional[int] = None):
        p = {"album": album}
        if limit is not None: p["limit"] = limit
        if page is not None: p["page"] = page
        return self._request("album.search", p)

# ---------- Artist ----------
class ArtistAPI(LastfmAPIBase):
    def add_tags(self, artist: str, tags: str, sk: Optional[str] = None):
        p = {"artist": artist, "tags": tags}
        if sk: p["sk"] = sk
        return self._request("artist.addtags", p, "POST")

    def get_correction(self, artist: str):
        return self._request("artist.getcorrection", {"artist": artist})

    def get_info(self, artist: Optional[str] = None, mbid: Optional[str] = None,
                 lang: Optional[str] = None, autocorrect: Optional[int] = None, username: Optional[str] = None):
        p = {}
        if artist: p["artist"] = artist
        if mbid: p["mbid"] = mbid
        if lang: p["lang"] = lang
        if autocorrect is not None: p["autocorrect"] = autocorrect
        if username: p["username"] = username
        return self._request("artist.getinfo", p)

    def get_similar(self, artist: Optional[str] = None, mbid: Optional[str] = None,
                    autocorrect: Optional[int] = None, limit: Optional[int] = None):
        p = {}
        if artist: p["artist"] = artist
        if mbid: p["mbid"] = mbid
        if autocorrect is not None: p["autocorrect"] = autocorrect
        if limit is not None: p["limit"] = limit
        return self._request("artist.getsimilar", p)

    def get_tags(self, artist: Optional[str] = None, mbid: Optional[str] = None,
                 user: Optional[str] = None, autocorrect: Optional[int] = None):
        p = {}
        if artist: p["artist"] = artist
        if mbid: p["mbid"] = mbid
        if user: p["user"] = user
        if autocorrect is not None: p["autocorrect"] = autocorrect
        return self._request("artist.gettags", p)

    def get_top_albums(self, artist: Optional[str] = None, mbid: Optional[str] = None,
                       autocorrect: Optional[int] = None, page: Optional[int] = None, limit: Optional[int] = None):
        p = {}
        if artist: p["artist"] = artist
        if mbid: p["mbid"] = mbid
        if autocorrect is not None: p["autocorrect"] = autocorrect
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("artist.gettopalbums", p)

    def get_top_tags(self, artist: Optional[str] = None, mbid: Optional[str] = None,
                     autocorrect: Optional[int] = None):
        p = {}
        if artist: p["artist"] = artist
        if mbid: p["mbid"] = mbid
        if autocorrect is not None: p["autocorrect"] = autocorrect
        return self._request("artist.gettoptags", p)

    def get_top_tracks(self, artist: Optional[str] = None, mbid: Optional[str] = None,
                       autocorrect: Optional[int] = None, page: Optional[int] = None, limit: Optional[int] = None):
        p = {}
        if artist: p["artist"] = artist
        if mbid: p["mbid"] = mbid
        if autocorrect is not None: p["autocorrect"] = autocorrect
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("artist.gettoptracks", p)

    def remove_tag(self, artist: str, tag: str, sk: Optional[str] = None):
        p = {"artist": artist, "tag": tag}
        if sk: p["sk"] = sk
        return self._request("artist.removetag", p, "POST")

    def search(self, artist: str, limit: Optional[int] = None, page: Optional[int] = None):
        p = {"artist": artist}
        if limit is not None: p["limit"] = limit
        if page is not None: p["page"] = page
        return self._request("artist.search", p)

# ---------- Auth ----------
class AuthAPI(LastfmAPIBase):
    def get_mobile_session(self, username: str, password: str):
        p = {"username": username, "password": password}
        return self._request("auth.getmobilesession", p, "POST")

    def get_session(self, token: str):
        return self._request("auth.getsession", {"token": token}, "POST")

    def get_token(self):
        return self._request("auth.gettoken", {})

# ---------- Chart ----------
class ChartAPI(LastfmAPIBase):
    def get_top_artists(self, page: Optional[int] = None, limit: Optional[int] = None):
        p = {}
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("chart.gettopartists", p)
    def get_top_tags(self, page: Optional[int] = None, limit: Optional[int] = None):
        p = {}
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("chart.gettoptags", p)
    def get_top_tracks(self, page: Optional[int] = None, limit: Optional[int] = None):
        p = {}
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("chart.gettoptracks", p)

# ---------- Geo ----------
class GeoAPI(LastfmAPIBase):
    def get_top_artists(self, country: str, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"country": country}
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("geo.gettopartists", p)
    def get_top_tracks(self, country: str, location: Optional[str] = None, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"country": country}
        if location: p["location"] = location
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("geo.gettoptracks", p)

# ---------- Library ----------
class LibraryAPI(LastfmAPIBase):
    def get_artists(self, user: str, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"user": user}
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("library.getartists", p)

# ---------- Tag ----------
class TagAPI(LastfmAPIBase):
    def get_info(self, tag: str, lang: Optional[str] = None):
        p = {"tag": tag}
        if lang: p["lang"] = lang
        return self._request("tag.getinfo", p)
    def get_similar(self, tag: str):
        return self._request("tag.getsimilar", {"tag": tag})
    def get_top_albums(self, tag: str, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"tag": tag}
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("tag.gettopalbums", p)
    def get_top_artists(self, tag: str, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"tag": tag}
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("tag.gettopartists", p)
    def get_top_tags(self):
        return self._request("tag.gettoptags", {})
    def get_top_tracks(self, tag: str, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"tag": tag}
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("tag.gettoptracks", p)
    def get_weekly_chart_list(self, tag: str):
        return self._request("tag.getweeklychartlist", {"tag": tag})

# ---------- Track ----------
class TrackAPI(LastfmAPIBase):
    def add_tags(self, artist: str, track: str, tags: str, sk: Optional[str] = None):
        p = {"artist": artist, "track": track, "tags": tags}
        if sk: p["sk"] = sk
        return self._request("track.addtags", p, "POST")
    def get_correction(self, artist: str, track: str):
        return self._request("track.getcorrection", {"artist": artist, "track": track})
    def get_info(self, artist: Optional[str] = None, track: Optional[str] = None, mbid: Optional[str] = None,
                 autocorrect: Optional[int] = None, username: Optional[str] = None):
        p = {}
        if artist: p["artist"] = artist
        if track: p["track"] = track
        if mbid: p["mbid"] = mbid
        if autocorrect is not None: p["autocorrect"] = autocorrect
        if username: p["username"] = username
        return self._request("track.getinfo", p)
    def get_similar(self, artist: Optional[str] = None, track: Optional[str] = None, mbid: Optional[str] = None,
                    autocorrect: Optional[int] = None, limit: Optional[int] = None):
        p = {}
        if artist: p["artist"] = artist
        if track: p["track"] = track
        if mbid: p["mbid"] = mbid
        if autocorrect is not None: p["autocorrect"] = autocorrect
        if limit is not None: p["limit"] = limit
        return self._request("track.getsimilar", p)
    def get_tags(self, artist: Optional[str] = None, track: Optional[str] = None, mbid: Optional[str] = None,
                 user: Optional[str] = None, autocorrect: Optional[int] = None):
        p = {}
        if artist: p["artist"] = artist
        if track: p["track"] = track
        if mbid: p["mbid"] = mbid
        if user: p["user"] = user
        if autocorrect is not None: p["autocorrect"] = autocorrect
        return self._request("track.gettags", p)
    def get_top_tags(self, artist: Optional[str] = None, track: Optional[str] = None, mbid: Optional[str] = None,
                     autocorrect: Optional[int] = None):
        p = {}
        if artist: p["artist"] = artist
        if track: p["track"] = track
        if mbid: p["mbid"] = mbid
        if autocorrect is not None: p["autocorrect"] = autocorrect
        return self._request("track.gettoptags", p)
    def love(self, artist: str, track: str, sk: Optional[str] = None):
        p = {"artist": artist, "track": track}
        if sk: p["sk"] = sk
        return self._request("track.love", p, "POST")
    def remove_tag(self, artist: str, track: str, tag: str, sk: Optional[str] = None):
        p = {"artist": artist, "track": track, "tag": tag}
        if sk: p["sk"] = sk
        return self._request("track.removetag", p, "POST")
    def scrobble(self, artist: str, track: str, timestamp: int, album: Optional[str] = None,
                 album_artist: Optional[str] = None, track_number: Optional[int] = None,
                 mbid: Optional[str] = None, duration: Optional[int] = None, sk: Optional[str] = None):
        p = {"artist": artist, "track": track, "timestamp": timestamp}
        if album: p["album"] = album
        if album_artist: p["albumArtist"] = album_artist
        if track_number is not None: p["trackNumber"] = track_number
        if mbid: p["mbid"] = mbid
        if duration is not None: p["duration"] = duration
        if sk: p["sk"] = sk
        return self._request("track.scrobble", p, "POST")
    def search(self, track: str, artist: Optional[str] = None, limit: Optional[int] = None, page: Optional[int] = None):
        p = {"track": track}
        if artist: p["artist"] = artist
        if limit is not None: p["limit"] = limit
        if page is not None: p["page"] = page
        return self._request("track.search", p)
    def unlove(self, artist: str, track: str, sk: Optional[str] = None):
        p = {"artist": artist, "track": track}
        if sk: p["sk"] = sk
        return self._request("track.unlove", p, "POST")
    def update_now_playing(self, artist: str, track: str, album: Optional[str] = None,
                           album_artist: Optional[str] = None, track_number: Optional[int] = None,
                           duration: Optional[int] = None, mbid: Optional[str] = None, sk: Optional[str] = None):
        p = {"artist": artist, "track": track}
        if album: p["album"] = album
        if album_artist: p["albumArtist"] = album_artist
        if track_number is not None: p["trackNumber"] = track_number
        if duration is not None: p["duration"] = duration
        if mbid: p["mbid"] = mbid
        if sk: p["sk"] = sk
        return self._request("track.updatenowplaying", p, "POST")

# ---------- User ----------
class UserAPI(LastfmAPIBase):
    def get_friends(self, user: str, recent_tracks: Optional[bool] = None, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"user": user}
        if recent_tracks is not None: p["recenttracks"] = int(bool(recent_tracks))
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("user.getfriends", p)
    def get_info(self, user: Optional[str] = None):
        p = {}
        if user: p["user"] = user
        return self._request("user.getinfo", p)
    def get_loved_tracks(self, user: str, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"user": user}
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("user.getlovedtracks", p)
    def get_personal_tags(self, user: str, tag: str, tagging_type: str):
        p = {"user": user, "tag": tag, "taggingtype": tagging_type}
        return self._request("user.getpersonaltags", p)
    def get_recent_tracks(self, user: str, page: Optional[int] = None, limit: Optional[int] = None,
                          from_timestamp: Optional[int] = None, to_timestamp: Optional[int] = None):
        p = {"user": user}
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        if from_timestamp is not None: p["from"] = from_timestamp
        if to_timestamp is not None: p["to"] = to_timestamp
        return self._request("user.getrecenttracks", p)
    def get_top_albums(self, user: str, period: Optional[str] = None, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"user": user}
        if period: p["period"] = period
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("user.gettopalbums", p)
    def get_top_artists(self, user: str, period: Optional[str] = None, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"user": user}
        if period: p["period"] = period
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("user.gettopartists", p)
    def get_top_tags(self, user: str):
        return self._request("user.gettoptags", {"user": user})
    def get_top_tracks(self, user: str, period: Optional[str] = None, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"user": user}
        if period: p["period"] = period
        if page is not None: p["page"] = page
        if limit is not None: p["limit"] = limit
        return self._request("user.gettoptracks", p)
    def get_weekly_album_chart(self, user: str, from_timestamp: Optional[int] = None, to_timestamp: Optional[int] = None):
        p = {"user": user}
        if from_timestamp is not None: p["from"] = from_timestamp
        if to_timestamp is not None: p["to"] = to_timestamp
        return self._request("user.getweeklyalbumchart", p)
    def get_weekly_artist_chart(self, user: str, from_timestamp: Optional[int] = None, to_timestamp: Optional[int] = None):
        p = {"user": user}
        if from_timestamp is not None: p["from"] = from_timestamp
        if to_timestamp is not None: p["to"] = to_timestamp
        return self._request("user.getweeklyartistchart", p)
    def get_weekly_chart_list(self, user: str):
        return self._request("user.getweeklychartlist", {"user": user})
    def get_weekly_track_chart(self, user: str, from_timestamp: Optional[int] = None, to_timestamp: Optional[int] = None):
        p = {"user": user}
        if from_timestamp is not None: p["from"] = from_timestamp
        if to_timestamp is not None: p["to"] = to_timestamp
        return self._request("user.getweeklytrackchart", p)
