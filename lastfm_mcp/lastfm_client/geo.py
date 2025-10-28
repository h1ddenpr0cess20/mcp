from typing import Optional
from .base import LastfmAPIBase


class GeoAPI(LastfmAPIBase):
    def get_top_artists(self, country: str, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"country": country}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("geo.gettopartists", p)

    def get_top_tracks(self, country: str, location: Optional[str] = None, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"country": country}
        if location:
            p["location"] = location
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("geo.gettoptracks", p)
