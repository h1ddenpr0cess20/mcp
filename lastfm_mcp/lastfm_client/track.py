from typing import Optional
from .base import LastfmAPIBase


class TrackAPI(LastfmAPIBase):
    """API client for track-related Last.fm operations."""

    def add_tags(
        self,
        artist: str,
        track: str,
        tags: str,
        sk: Optional[str] = None
    ):
        """Tag a track.

        Args:
            artist: The artist name.
            track: The track name.
            tags: Comma-separated list of tags.
            sk: Session key for authentication (optional, uses default if not provided).

        Returns:
            Dict containing the API response.
        """
        p = {"artist": artist, "track": track, "tags": tags}
        if sk:
            p["sk"] = sk
        return self._request("track.addtags", p, "POST")

    def get_correction(
        self,
        artist: str,
        track: str
    ):
        """Canonical correction for track.

        Args:
            artist: The artist name.
            track: The track name.

        Returns:
            Dict containing corrected track information.
        """
        return self._request("track.getcorrection", {"artist": artist, "track": track})

    def get_info(
        self,
        artist: Optional[str] = None,
        track: Optional[str] = None,
        mbid: Optional[str] = None,
        autocorrect: Optional[int] = None,
        username: Optional[str] = None,
    ):
        """Track info.

        Args:
            artist: The artist name.
            track: The track name.
            mbid: MusicBrainz ID.
            autocorrect: Whether to autocorrect misspelled artist/track names (0 or 1).
            username: Username for additional user-specific info.

        Returns:
            Dict containing track information.
        """
        p = {}
        if artist:
            p["artist"] = artist
        if track:
            p["track"] = track
        if mbid:
            p["mbid"] = mbid
        if autocorrect is not None:
            p["autocorrect"] = autocorrect
        if username:
            p["username"] = username
        return self._request("track.getinfo", p)

    def get_similar(
        self,
        artist: Optional[str] = None,
        track: Optional[str] = None,
        mbid: Optional[str] = None,
        autocorrect: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        """Similar tracks.

        Args:
            artist: The artist name.
            track: The track name.
            mbid: MusicBrainz ID.
            autocorrect: Whether to autocorrect misspelled artist/track names (0 or 1).
            limit: Maximum number of similar tracks to return.

        Returns:
            Dict containing similar tracks.
        """
        p = {}
        if artist:
            p["artist"] = artist
        if track:
            p["track"] = track
        if mbid:
            p["mbid"] = mbid
        if autocorrect is not None:
            p["autocorrect"] = autocorrect
        if limit is not None:
            p["limit"] = limit
        return self._request("track.getsimilar", p)

    def get_tags(
        self,
        artist: Optional[str] = None,
        track: Optional[str] = None,
        mbid: Optional[str] = None,
        user: Optional[str] = None,
        autocorrect: Optional[int] = None,
    ):
        """User's tags for a track.

        Args:
            artist: The artist name.
            track: The track name.
            mbid: MusicBrainz ID.
            user: The username to get tags for.
            autocorrect: Whether to autocorrect misspelled artist/track names (0 or 1).

        Returns:
            Dict containing user tags for the track.
        """
        p = {}
        if artist:
            p["artist"] = artist
        if track:
            p["track"] = track
        if mbid:
            p["mbid"] = mbid
        if user:
            p["user"] = user
        if autocorrect is not None:
            p["autocorrect"] = autocorrect
        return self._request("track.gettags", p)

    def get_top_tags(
        self,
        artist: Optional[str] = None,
        track: Optional[str] = None,
        mbid: Optional[str] = None,
        autocorrect: Optional[int] = None,
    ):
        """Top tags for a track.

        Args:
            artist: The artist name.
            track: The track name.
            mbid: MusicBrainz ID.
            autocorrect: Whether to autocorrect misspelled artist/track names (0 or 1).

        Returns:
            Dict containing top tags for the track.
        """
        p = {}
        if artist:
            p["artist"] = artist
        if track:
            p["track"] = track
        if mbid:
            p["mbid"] = mbid
        if autocorrect is not None:
            p["autocorrect"] = autocorrect
        return self._request("track.gettoptags", p)

    def love(
        self,
        artist: str,
        track: str,
        sk: Optional[str] = None
    ):
        """Mark a track as loved.

        Args:
            artist: The artist name.
            track: The track name.
            sk: Session key for authentication (optional, uses default if not provided).

        Returns:
            Dict containing the API response.
        """
        p = {"artist": artist, "track": track}
        if sk:
            p["sk"] = sk
        return self._request("track.love", p, "POST")

    def remove_tag(
        self,
        artist: str,
        track: str,
        tag: str,
        sk: Optional[str] = None
    ):
        """Remove a tag from a track.

        Args:
            artist: The artist name.
            track: The track name.
            tag: The tag to remove.
            sk: Session key for authentication (optional, uses default if not provided).

        Returns:
            Dict containing the API response.
        """
        p = {"artist": artist, "track": track, "tag": tag}
        if sk:
            p["sk"] = sk
        return self._request("track.removetag", p, "POST")

    def scrobble(
        self,
        artist: str,
        track: str,
        timestamp: int,
        album: Optional[str] = None,
        album_artist: Optional[str] = None,
        track_number: Optional[int] = None,
        mbid: Optional[str] = None,
        duration: Optional[int] = None,
        sk: Optional[str] = None,
    ):
        """Add a scrobble.

        Args:
            artist: The artist name.
            track: The track name.
            timestamp: Unix timestamp of when the track was listened.
            album: The album name.
            album_artist: The album artist name.
            track_number: The track number on the album.
            mbid: MusicBrainz ID.
            duration: The track duration in seconds.
            sk: Session key for authentication (optional, uses default if not provided).

        Returns:
            Dict containing the API response.
        """
        p = {"artist": artist, "track": track, "timestamp": timestamp}
        if album:
            p["album"] = album
        if album_artist:
            p["albumArtist"] = album_artist
        if track_number is not None:
            p["trackNumber"] = track_number
        if mbid:
            p["mbid"] = mbid
        if duration is not None:
            p["duration"] = duration
        if sk:
            p["sk"] = sk
        return self._request("track.scrobble", p, "POST")

    def search(
        self,
        track: str,
        artist: Optional[str] = None,
        limit: Optional[int] = None,
        page: Optional[int] = None,
    ):
        """Search for tracks.

        Args:
            track: The track name to search for.
            artist: The artist name (optional filter).
            limit: Number of results to return.
            page: Page number for pagination.

        Returns:
            Dict containing search results.
        """
        p = {"track": track}
        if artist:
            p["artist"] = artist
        if limit is not None:
            p["limit"] = limit
        if page is not None:
            p["page"] = page
        return self._request("track.search", p)

    def unlove(
        self,
        artist: str,
        track: str,
        sk: Optional[str] = None
    ):
        """Unmark loved.

        Args:
            artist: The artist name.
            track: The track name.
            sk: Session key for authentication (optional, uses default if not provided).

        Returns:
            Dict containing the API response.
        """
        p = {"artist": artist, "track": track}
        if sk:
            p["sk"] = sk
        return self._request("track.unlove", p, "POST")

    def update_now_playing(
        self,
        artist: str,
        track: str,
        album: Optional[str] = None,
        album_artist: Optional[str] = None,
        track_number: Optional[int] = None,
        duration: Optional[int] = None,
        mbid: Optional[str] = None,
        sk: Optional[str] = None,
    ):
        """Set now playing.

        Args:
            artist: The artist name.
            track: The track name.
            album: The album name.
            album_artist: The album artist name.
            track_number: The track number on the album.
            duration: The track duration in seconds.
            mbid: MusicBrainz ID.
            sk: Session key for authentication (optional, uses default if not provided).

        Returns:
            Dict containing the API response.
        """
        p = {"artist": artist, "track": track}
        if album:
            p["album"] = album
        if album_artist:
            p["albumArtist"] = album_artist
        if track_number is not None:
            p["trackNumber"] = track_number
        if duration is not None:
            p["duration"] = duration
        if mbid:
            p["mbid"] = mbid
        if sk:
            p["sk"] = sk
        return self._request("track.updatenowplaying", p, "POST")
