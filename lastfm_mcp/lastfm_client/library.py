from typing import Optional
from .base import LastfmAPIBase


class LibraryAPI(LastfmAPIBase):
    def get_artists(self, user: str, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"user": user}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("library.getartists", p)
