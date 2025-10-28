from typing import Optional
from .base import LastfmAPIBase


class ChartAPI(LastfmAPIBase):
    def get_top_artists(self, page: Optional[int] = None, limit: Optional[int] = None):
        p = {}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("chart.gettopartists", p)

    def get_top_tags(self, page: Optional[int] = None, limit: Optional[int] = None):
        p = {}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("chart.gettoptags", p)

    def get_top_tracks(self, page: Optional[int] = None, limit: Optional[int] = None):
        p = {}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("chart.gettoptracks", p)
