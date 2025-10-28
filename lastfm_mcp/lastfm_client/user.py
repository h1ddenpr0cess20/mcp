from typing import Optional
from .base import LastfmAPIBase


class UserAPI(LastfmAPIBase):
    """API client for user-related Last.fm operations."""

    def get_friends(
        self,
        user: str,
        recent_tracks: Optional[bool] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        """Get a user's friends.

        Args:
            user: Username whose friends to retrieve.
            recent_tracks: Whether to include recent tracks for friends.
            page: Page number for pagination.
            limit: Number of results per page.

        Returns:
            Dict containing user's friends.
        """
        p = {"user": user}
        if recent_tracks is not None:
            p["recenttracks"] = int(bool(recent_tracks))
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("user.getfriends", p)

    def get_info(
        self,
        user: Optional[str] = None
    ):
        """Get user profile info.

        Args:
            user: Username to get info for.

        Returns:
            Dict containing user profile information.
        """
        p = {}
        if user:
            p["user"] = user
        return self._request("user.getinfo", p)

    def get_loved_tracks(
        self,
        user: str,
        page: Optional[int] = None,
        limit: Optional[int] = None
    ):
        """Loved tracks by user.

        Args:
            user: Username whose loved tracks to retrieve.
            page: Page number for pagination.
            limit: Number of results per page.

        Returns:
            Dict containing user's loved tracks.
        """
        p = {"user": user}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("user.getlovedtracks", p)

    def get_personal_tags(
        self,
        user: str,
        tag: str,
        tagging_type: str
    ):
        """Personal tags for a type (artist/album/track).

        Args:
            user: Username whose personal tags to retrieve.
            tag: The personal tag name.
            tagging_type: Type to retrieve tags for ('artist', 'album', 'track').

        Returns:
            Dict containing personal tags for the specified type.
        """
        p = {"user": user, "tag": tag, "taggingtype": tagging_type}
        return self._request("user.getpersonaltags", p)

    def get_recent_tracks(
        self,
        user: str,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        from_timestamp: Optional[int] = None,
        to_timestamp: Optional[int] = None,
    ):
        """Recent tracks listened by user.

        Args:
            user: Username whose recent tracks to retrieve.
            page: Page number for pagination.
            limit: Number of results per page.
            from_timestamp: Unix timestamp to start from.
            to_timestamp: Unix timestamp to end at.

        Returns:
            Dict containing user's recent tracks.
        """
        p = {"user": user}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        if from_timestamp is not None:
            p["from"] = from_timestamp
        if to_timestamp is not None:
            p["to"] = to_timestamp
        return self._request("user.getrecenttracks", p)

    def get_top_albums(
        self,
        user: str,
        period: Optional[str] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        """User's top albums.

        Args:
            user: Username whose top albums to retrieve.
            period: Time period ('overall', '7day', '1month', etc.).
            page: Page number for pagination.
            limit: Number of results per page.

        Returns:
            Dict containing user's top albums.
        """
        p = {"user": user}
        if period:
            p["period"] = period
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("user.gettopalbums", p)

    def get_top_artists(
        self,
        user: str,
        period: Optional[str] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        """User's top artists.

        Args:
            user: Username whose top artists to retrieve.
            period: Time period ('overall', '7day', '1month', etc.).
            page: Page number for pagination.
            limit: Number of results per page.

        Returns:
            Dict containing user's top artists.
        """
        p = {"user": user}
        if period:
            p["period"] = period
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("user.gettopartists", p)

    def get_top_tags(
        self,
        user: str
    ):
        """User's top tags.

        Args:
            user: Username whose top tags to retrieve.

        Returns:
            Dict containing user's top tags.
        """
        return self._request("user.gettoptags", {"user": user})

    def get_top_tracks(
        self,
        user: str,
        period: Optional[str] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        """User's top tracks.

        Args:
            user: Username whose top tracks to retrieve.
            period: Time period ('overall', '7day', '1month', etc.).
            page: Page number for pagination.
            limit: Number of results per page.

        Returns:
            Dict containing user's top tracks.
        """
        p = {"user": user}
        if period:
            p["period"] = period
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("user.gettoptracks", p)

    def get_weekly_album_chart(
        self,
        user: str,
        from_timestamp: Optional[int] = None,
        to_timestamp: Optional[int] = None,
    ):
        """Weekly album chart for user.

        Args:
            user: Username whose weekly album chart to retrieve.
            from_timestamp: Unix timestamp for start of week.
            to_timestamp: Unix timestamp for end of week.

        Returns:
            Dict containing weekly album chart data.
        """
        p = {"user": user}
        if from_timestamp is not None:
            p["from"] = from_timestamp
        if to_timestamp is not None:
            p["to"] = to_timestamp
        return self._request("user.getweeklyalbumchart", p)

    def get_weekly_artist_chart(
        self,
        user: str,
        from_timestamp: Optional[int] = None,
        to_timestamp: Optional[int] = None,
    ):
        """Weekly artist chart for user.

        Args:
            user: Username whose weekly artist chart to retrieve.
            from_timestamp: Unix timestamp for start of week.
            to_timestamp: Unix timestamp for end of week.

        Returns:
            Dict containing weekly artist chart data.
        """
        p = {"user": user}
        if from_timestamp is not None:
            p["from"] = from_timestamp
        if to_timestamp is not None:
            p["to"] = to_timestamp
        return self._request("user.getweeklyartistchart", p)

    def get_weekly_chart_list(
        self,
        user: str
    ):
        """Available weekly chart ranges for user.

        Args:
            user: Username whose weekly chart list to retrieve.

        Returns:
            Dict containing available weekly chart date ranges.
        """
        return self._request("user.getweeklychartlist", {"user": user})

    def get_weekly_track_chart(
        self,
        user: str,
        from_timestamp: Optional[int] = None,
        to_timestamp: Optional[int] = None,
    ):
        """Weekly track chart for user.

        Args:
            user: Username whose weekly track chart to retrieve.
            from_timestamp: Unix timestamp for start of week.
            to_timestamp: Unix timestamp for end of week.

        Returns:
            Dict containing weekly track chart data.
        """
        p = {"user": user}
        if from_timestamp is not None:
            p["from"] = from_timestamp
        if to_timestamp is not None:
            p["to"] = to_timestamp
        return self._request("user.getweeklytrackchart", p)
