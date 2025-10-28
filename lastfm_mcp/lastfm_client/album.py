from typing import Optional
from .base import LastfmAPIBase


class AlbumAPI(LastfmAPIBase):
    """API client for album-related Last.fm operations."""

    def add_tags(
        self,
        artist: str,
        album: str,
        tags: str,
        sk: Optional[str] = None
    ):
        """Tag an album.

        Args:
            artist: The artist name.
            album: The album name.
            tags: Comma-separated list of tags.
            sk: Session key for authentication (optional, uses default if not provided).

        Returns:
            Dict containing the API response.
        """
        p = {"artist": artist, "album": album, "tags": tags}
        if sk:
            p["sk"] = sk
        return self._request("album.addtags", p, "POST")

    def get_info(
        self,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        mbid: Optional[str] = None,
        autocorrect: Optional[int] = None,
        username: Optional[str] = None,
        lang: Optional[str] = None,
    ):
        """Get album metadata and tracks.

        Args:
            artist: The artist name.
            album: The album name.
            mbid: MusicBrainz ID.
            autocorrect: Whether to autocorrect misspelled artist/album names (0 or 1).
            username: Username to retrieve album from their library.
            lang: Language for descriptions (ISO 639-1 alpha-2).

        Returns:
            Dict containing album information.
        """
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

    def get_tags(
        self,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        mbid: Optional[str] = None,
        autocorrect: Optional[int] = None,
        user: Optional[str] = None,
    ):
        """Get a user's tags for an album.

        Args:
            artist: The artist name.
            album: The album name.
            mbid: MusicBrainz ID.
            autocorrect: Whether to autocorrect misspelled names.
            user: The username to get tags for.

        Returns:
            Dict containing album tags.
        """
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

    def get_top_tags(
        self,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        mbid: Optional[str] = None,
        autocorrect: Optional[int] = None,
    ):
        """Get top tags for an album.

        Args:
            artist: The artist name.
            album: The album name.
            mbid: MusicBrainz ID.
            autocorrect: Whether to autocorrect misspelled names.

        Returns:
            Dict containing top album tags.
        """
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

    def remove_tag(
            self,
            artist: str,
            album: str,
            tag: str,
            sk: Optional[str] = None):
        """Remove a tag from an album (requires auth).

        Args:
            artist: The artist name.
            album: The album name.
            tag: The tag to remove.
            sk: Session key for authentication.

        Returns:
            Dict containing the API response.
        """
        p = {"artist": artist, "album": album, "tag": tag}
        if sk:
            p["sk"] = sk
        return self._request("album.removetag", p, "POST")

    def search(
        self,
        album: str,
        limit: Optional[int] = None,
        page: Optional[int] = None
    ):
        """Search for albums.

        Args:
            album: The album name to search for.
            limit: Number of results to return.
            page: Page number for pagination.

        Returns:
            Dict containing search results.
        """
        p = {"album": album}
        if limit is not None:
            p["limit"] = limit
        if page is not None:
            p["page"] = page
        return self._request("album.search", p)
