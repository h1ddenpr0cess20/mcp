from typing import Optional
from .base import LastfmAPIBase


class GeoAPI(LastfmAPIBase):
    """API client for geographic chart data operations."""

    def get_top_artists(
        self, country: str, page: Optional[int] = None, limit: Optional[int] = None
    ):
        """Top artists by country.

        Args:
            country: Country name.
            page: Page number for pagination.
            limit: Number of results per page.

        Returns:
            Dict containing top artists by country.
        """
        p = {"country": country}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("geo.gettopartists", p)

    def get_top_tracks(
        self,
        country: str,
        location: Optional[str] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        """Top tracks by country/metro.

        Args:
            country: Country name.
            location: Metro or city name (e.g., "Manchester" for UK).
            page: Page number for pagination.
            limit: Number of results per page.

        Returns:
            Dict containing top tracks by location.
        """
        p = {"country": country}
        if location:
            p["location"] = location
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("geo.gettoptracks", p)
