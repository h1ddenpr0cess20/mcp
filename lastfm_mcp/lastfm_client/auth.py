from .base import LastfmAPIBase


class AuthAPI(LastfmAPIBase):
    """API client for Last.fm authentication operations."""

    def get_mobile_session(
        self,
        username: str,
        password: str
    ):
        """Exchange username/password for session (mobile).

        Args:
            username: Last.fm username.
            password: Last.fm password.

        Returns:
            Dict containing session information.
        """
        p = {"username": username, "password": password}
        return self._request("auth.getmobilesession", p, "POST")

    def get_session(
        self,
        token: str
    ):
        """Exchange token for session.

        Args:
            token: Unauthorized token obtained earlier.

        Returns:
            Dict containing session information.
        """
        return self._request("auth.getsession", {"token": token}, "POST")

    def get_token(self):
        """Get an unauthorized token.

        Returns:
            Dict containing an unauthorized token for authentication flow.
        """
        return self._request("auth.gettoken", {})
