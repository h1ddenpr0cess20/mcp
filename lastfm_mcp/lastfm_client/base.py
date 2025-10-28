import hashlib
import os
from typing import Any, Dict, Optional

import requests

BASE_URL = "https://ws.audioscrobbler.com/2.0/"


class LastfmAPIBase:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, session_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LASTFM_API_KEY", "")
        self.api_secret = api_secret or os.getenv("LASTFM_API_SECRET", "")
        self.session_key = session_key or os.getenv("LASTFM_SESSION_KEY", "")

        if not self.api_key:
            raise RuntimeError("LASTFM_API_KEY is required")

    def _signature(self, params: Dict[str, Any]) -> str:
        """Build api_sig per Last.fm: sort keys, concat key+value, append secret, md5."""
        pieces = []
        for k in sorted(params.keys()):
            if k in {"format", "callback", "api_sig"}:
                continue
            pieces.append(f"{k}{params[k]}")
        raw = "".join(pieces) + self.api_secret
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _request(self, method: str, params: Dict[str, Any], http_method: str = "GET"):
        params = {**params}
        params["api_key"] = self.api_key
        params["format"] = "json"
        params["method"] = method

        if http_method == "POST":
            # Need session key + signature
            if not params.get("sk"):
                if not self.session_key:
                    raise RuntimeError("This method requires a Last.fm session key. Provide LASTFM_SESSION_KEY or pass sk.")
                params["sk"] = self.session_key
            if not self.api_secret:
                raise RuntimeError("This method requires LASTFM_API_SECRET for signing.")
            params["api_sig"] = self._signature(params)
            r = requests.post(BASE_URL, data=params, timeout=30)
        else:
            r = requests.get(BASE_URL, params=params, timeout=30)

        r.raise_for_status()
        return r.json()
