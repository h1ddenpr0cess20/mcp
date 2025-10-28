from typing import Optional
from .base import LastfmAPIBase


class TagAPI(LastfmAPIBase):
    """API client for tag-related operations."""

    def get_info(
        self,
        tag: str,
        lang: Optional[str] = None
    ):
        """Tag metadata and wiki.

        Args:
            tag: The tag name.
            lang: Language for wiki content (ISO 639-1 alpha-2).

        Returns:
            Dict containing tag information.
        """
        p = {"tag": tag}
        if lang:
            p["lang"] = lang
        return self._request("tag.getinfo", p)

    def get_similar(
        self,
        tag: str
    ):
        """Similar tags.

        Args:
            tag: The tag name to find similar tags for.

        Returns:
            Dict containing similar tags.
        """
        return self._request("tag.getsimilar", {"tag": tag})

    def get_top_albums(
        self,
        tag: str,
        page: Optional[int] = None,
        limit: Optional[int] = None
    ):
        """Top albums for a tag.

        Args:
            tag: The tag name.
            page: Page number for pagination.
            limit: Number of results per page.

        Returns:
            Dict containing top albums for the tag.
        """
        p = {"tag": tag}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("tag.gettopalbums", p)

    def get_top_artists(
        self,
        tag: str,
        page: Optional[int] = None,
        limit: Optional[int] = None
    ):
        """Top artists for a tag.

        Args:
            tag: The tag name.
            page: Page number for pagination.
            limit: Number of results per page.

        Returns:
            Dict containing top artists for the tag.
        """
        p = {"tag": tag}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("tag.gettopartists", p)

    def get_top_tags(self):
        """Global top tags.

        Returns:
            Dict containing global top tags.
        """
        return self._request("tag.gettoptags", {})

    def get_top_tracks(
        self,
        tag: str,
        page: Optional[int] = None,
        limit: Optional[int] = None
    ):
        """Top tracks for a tag.

        Args:
            tag: The tag name.
            page: Page number for pagination.
            limit: Number of results per page.

        Returns:
            Dict containing top tracks for the tag.
        """
        p = {"tag": tag}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("tag.gettoptracks", p)

    def get_weekly_chart_list(
        self,
        tag: str
    ):
        """Weekly chart date ranges for a tag.

        Args:
            tag: The tag name.

        Returns:
            Dict containing available weekly chart date ranges.
        """
        return self._request("tag.getweeklychartlist", {"tag": tag})
