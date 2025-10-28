from typing import Optional
from .base import LastfmAPIBase


class ChartAPI(LastfmAPIBase):
    """API client for global chart data operations."""

    def get_top_artists(
        self,
        page: Optional[int] = None,
        limit: Optional[int] = None
    ):
        """Global top artists.

        Args:
            page: Page number for pagination.
            limit: Number of results per page.

        Returns:
            Dict containing top artists chart data.
        """
        p = {}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("chart.gettopartists", p)

    def get_top_tags(
        self,
        page: Optional[int] = None,
        limit: Optional[int] = None
    ):
        """Global top tags.

        Args:
            page: Page number for pagination.
            limit: Number of results per page.

        Returns:
            Dict containing top tags chart data.
        """
        p = {}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("chart.gettoptags", p)

    def get_top_tracks(
        self,
        page: Optional[int] = None,
        limit: Optional[int] = None
    ):
        """Global top tracks.

        Args:
            page: Page number for pagination.
            limit: Number of results per page.

        Returns:
            Dict containing top tracks chart data.
        """
        p = {}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("chart.gettoptracks", p)
