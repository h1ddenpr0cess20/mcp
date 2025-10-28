import hashlib
import os
from typing import Any, Dict, Optional

import requests

BASE_URL = "https://ws.audioscrobbler.com/2.0/"


class LastfmAPIBase:
    """Base class for Last.fm API clients.

    Provides common functionality for authentication, request signing, and HTTP requests.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        session_key: Optional[str] = None,
    ):
        """Initialize the base API client.

        Args:
            api_key: Last.fm API key. If None, reads from LASTFM_API_KEY environment variable.
            api_secret: Last.fm API secret. If None, reads from LASTFM_API_SECRET environment variable.
            session_key: User session key. If None, reads from LASTFM_SESSION_KEY environment variable.

        Raises:
            RuntimeError: If api_key is not provided via parameter or environment variable.
        """
        self.api_key = api_key or os.getenv("LASTFM_API_KEY", "")
        self.api_secret = api_secret or os.getenv("LASTFM_API_SECRET", "")
        self.session_key = session_key or os.getenv("LASTFM_SESSION_KEY", "")

        if not self.api_key:
            raise RuntimeError("LASTFM_API_KEY is required")

    def _signature(
        self,
        params: Dict[str, Any]
    ) -> str:
        """Build api_sig per Last.fm: sort keys, concat key+value, append secret, md5."""
        pieces = []
        for k in sorted(params.keys()):
            if k in {"format", "callback", "api_sig"}:
                continue
            pieces.append(f"{k}{params[k]}")
        raw = "".join(pieces) + self.api_secret
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _request(self, method: str, params: Dict[str, Any], http_method: str = "GET"):
        """Make a request to the Last.fm API.

        Args:
            method: The Last.fm API method name.
            params: Dictionary of parameters for the API call.
            http_method: HTTP method to use ('GET' or 'POST').

        Returns:
            Dict containing the JSON response from the API.

        Raises:
            RuntimeError: If session key or API secret is missing for POST requests.
            requests.HTTPError: If the API returns a non-2xx status code.
        """
        params = {**params}
        params["api_key"] = self.api_key
        params["format"] = "json"
        params["method"] = method

        if http_method == "POST":
            # Need session key + signature
            if not params.get("sk"):
                if not self.session_key:
                    raise RuntimeError(
                        "This method requires a Last.fm session key. Provide LASTFM_SESSION_KEY or pass sk."
                    )
                params["sk"] = self.session_key
            if not self.api_secret:
                raise RuntimeError(
                    "This method requires LASTFM_API_SECRET for signing."
                )
            params["api_sig"] = self._signature(params)
            r = requests.post(BASE_URL, data=params, timeout=30)
        else:
            r = requests.get(BASE_URL, params=params, timeout=30)

        r.raise_for_status()
        return r.json()
