import json

import pytest
import requests

from blog_client import BlogClient


def make_response(status: int = 200, data=None, text: str | None = None, headers: dict | None = None) -> requests.Response:
    """A real requests.Response, so the client is tested against the same type it gets in production."""
    response = requests.Response()
    response.status_code = status
    response._content = (text if text is not None else json.dumps(data)).encode("utf-8")
    response.headers.update({"Content-Type": "application/json", **(headers or {})})
    return response


class FakeSession:
    """Stands in for requests.Session: records each call and answers from `responder(method, url, kwargs)`.

    The responder returns a Response, or an exception to raise."""

    def __init__(self, responder):
        self.responder = responder
        self.calls: list[dict] = []

    def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        result = self.responder(method, url, kwargs)
        if isinstance(result, Exception):
            raise result
        return result

    @property
    def last(self) -> dict:
        return self.calls[-1]


@pytest.fixture
def make_client():
    """Build (client, session) where every request is answered by `responder`."""

    def build(responder=lambda method, url, kwargs: make_response(200, {}), **options):
        session = FakeSession(responder)
        settings = {"base_url": "http://blog.test", "token": "test-token", "session": session, **options}
        return BlogClient(**settings), session

    return build
