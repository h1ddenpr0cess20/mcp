from .base import LastfmAPIBase


class AuthAPI(LastfmAPIBase):
    def get_mobile_session(self, username: str, password: str):
        p = {"username": username, "password": password}
        return self._request("auth.getmobilesession", p, "POST")

    def get_session(self, token: str):
        return self._request("auth.getsession", {"token": token}, "POST")

    def get_token(self):
        return self._request("auth.gettoken", {})
