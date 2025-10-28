from typing import Optional
from .base import LastfmAPIBase


class UserAPI(LastfmAPIBase):
    def get_friends(self,
                    user: str,
                    recent_tracks: Optional[bool] = None,
                    page: Optional[int] = None,
                    limit: Optional[int] = None):
        p = {"user": user}
        if recent_tracks is not None:
            p["recenttracks"] = int(bool(recent_tracks))
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("user.getfriends", p)

    def get_info(self, user: Optional[str] = None):
        p = {}
        if user:
            p["user"] = user
        return self._request("user.getinfo", p)

    def get_loved_tracks(self, user: str, page: Optional[int] = None, limit: Optional[int] = None):
        p = {"user": user}
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("user.getlovedtracks", p)

    def get_personal_tags(self, user: str, tag: str, tagging_type: str):
        p = {"user": user, "tag": tag, "taggingtype": tagging_type}
        return self._request("user.getpersonaltags", p)

    def get_recent_tracks(self,
                          user: str,
                          page: Optional[int] = None,
                          limit: Optional[int] = None,
                          from_timestamp: Optional[int] = None,
                          to_timestamp: Optional[int] = None):
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

    def get_top_albums(self,
                       user: str,
                       period: Optional[str] = None,
                       page: Optional[int] = None,
                       limit: Optional[int] = None):
        p = {"user": user}
        if period:
            p["period"] = period
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("user.gettopalbums", p)

    def get_top_artists(self,
                        user: str,
                        period: Optional[str] = None,
                        page: Optional[int] = None,
                        limit: Optional[int] = None):
        p = {"user": user}
        if period:
            p["period"] = period
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("user.gettopartists", p)

    def get_top_tags(self, user: str):
        return self._request("user.gettoptags", {"user": user})

    def get_top_tracks(self,
                       user: str,
                       period: Optional[str] = None,
                       page: Optional[int] = None,
                       limit: Optional[int] = None):
        p = {"user": user}
        if period:
            p["period"] = period
        if page is not None:
            p["page"] = page
        if limit is not None:
            p["limit"] = limit
        return self._request("user.gettoptracks", p)

    def get_weekly_album_chart(self,
                               user: str,
                               from_timestamp: Optional[int] = None,
                               to_timestamp: Optional[int] = None):
        p = {"user": user}
        if from_timestamp is not None:
            p["from"] = from_timestamp
        if to_timestamp is not None:
            p["to"] = to_timestamp
        return self._request("user.getweeklyalbumchart", p)

    def get_weekly_artist_chart(self,
                                user: str,
                                from_timestamp: Optional[int] = None,
                                to_timestamp: Optional[int] = None):
        p = {"user": user}
        if from_timestamp is not None:
            p["from"] = from_timestamp
        if to_timestamp is not None:
            p["to"] = to_timestamp
        return self._request("user.getweeklyartistchart", p)

    def get_weekly_chart_list(self, user: str):
        return self._request("user.getweeklychartlist", {"user": user})

    def get_weekly_track_chart(self,
                               user: str,
                               from_timestamp: Optional[int] = None,
                               to_timestamp: Optional[int] = None):
        p = {"user": user}
        if from_timestamp is not None:
            p["from"] = from_timestamp
        if to_timestamp is not None:
            p["to"] = to_timestamp
        return self._request("user.getweeklytrackchart", p)
