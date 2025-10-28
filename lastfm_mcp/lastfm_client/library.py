from typing import Optional
from .base import LastfmAPIBase


class LibraryAPI(LastfmAPIBase):
    """API client for user library operations."""

    def get_artists(
        self,
        user: str,
        page: Optional[int] = None,
        limit: Optional[int] = None
    ):
        """Artists in a user's library.

        Args:
            user: Username whose library to retrieve.
            page: Page number for pagination.
            limit: Number of results per page.

        Returns:
            Dict containing artists from user's library.
        """
        p = {"user": user}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("library.getartists", p)
