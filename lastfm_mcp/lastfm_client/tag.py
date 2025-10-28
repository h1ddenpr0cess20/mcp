from typing import Optional
from .base import LastfmAPIBase


class TagAPI(LastfmAPIBase):
    def get_info(self, tag: str, lang: Optional[str] = None):
        p = {"tag": tag}
        if lang:
            p["lang"] = lang
        return self._request("tag.getinfo", p)

    def get_similar(self, tag: str):
        return self._request("tag.getsimilar", {"tag": tag})

    def get_top_albums(self, tag: str, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"tag": tag}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("tag.gettopalbums", p)

    def get_top_artists(self, tag: str, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"tag": tag}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("tag.gettopartists", p)

    def get_top_tags(self):
        return self._request("tag.gettoptags", {})

    def get_top_tracks(self, tag: str, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"tag": tag}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("tag.gettoptracks", p)

    def get_weekly_chart_list(self, tag: str):
        return self._request("tag.getweeklychartlist", {"tag": tag})
