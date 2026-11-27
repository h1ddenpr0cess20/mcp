"""Tests for sessions, CSRF tokens, the API token, and login throttling."""

import time

import pytest

from blog_app.auth import SESSION_SECONDS, Auth, LoginThrottle
from blog_app.passwords import hash_password, verify_password


@pytest.fixture
def auth():
    return Auth("owner", hash_password("pw"), "s" * 32, "api-token-value")


class TestLogin:
    @pytest.mark.unit
    def test_accepts_only_the_right_pair(self, auth):
        assert auth.check_login("owner", "pw") is True
        assert auth.check_login("owner", "PW") is False
        assert auth.check_login("Owner", "pw") is False
        assert auth.check_login("", "") is False
        assert auth.check_login("owner", "pw ") is False

    @pytest.mark.unit
    def test_unicode_credentials_do_not_crash(self):
        auth = Auth("owner", hash_password("pässwörd-日本"), "s" * 32, "t")
        assert auth.check_login("owner", "pässwörd-日本") is True
        assert auth.check_login("owner", "passwörd-日本") is False


class TestSessions:
    @pytest.mark.unit
    def test_round_trip(self, auth):
        cookie, data = auth.new_session()
        read = auth.read_session(cookie)
        assert read["u"] == "owner"
        assert read["csrf"] == data["csrf"]
        assert read["exp"] > time.time()

    @pytest.mark.unit
    def test_each_session_gets_its_own_csrf_token(self, auth):
        assert auth.new_session()[1]["csrf"] != auth.new_session()[1]["csrf"]

    @pytest.mark.unit
    @pytest.mark.parametrize("cookie", [None, "", "nodot", ".", "a.b", "e30.e30", "\xff.\xff", "x" * 5000])
    def test_garbage_is_rejected(self, auth, cookie):
        assert auth.read_session(cookie) is None

    @pytest.mark.unit
    def test_tampered_payload_is_rejected(self, auth):
        cookie, _ = auth.new_session()
        raw, sig = cookie.split(".")
        forged = ("A" if raw[0] != "A" else "B") + raw[1:]
        assert auth.read_session(f"{forged}.{sig}") is None

    @pytest.mark.unit
    def test_tampered_signature_is_rejected(self, auth):
        cookie, _ = auth.new_session()
        raw, sig = cookie.split(".")
        changed = sig[:-1] + ("A" if sig[-1] != "A" else "B")  # always differs from the real signature
        assert auth.read_session(f"{raw}.{changed}") is None

    @pytest.mark.unit
    def test_session_signed_with_another_key_is_rejected(self, auth):
        other = Auth("owner", hash_password("pw"), "z" * 32, "t")
        assert auth.read_session(other.new_session()[0]) is None

    @pytest.mark.unit
    def test_expired_session_is_rejected(self, auth, monkeypatch):
        cookie, data = auth.new_session()
        monkeypatch.setattr(time, "time", lambda: data["exp"] + 1)
        assert auth.read_session(cookie) is None

    @pytest.mark.unit
    def test_session_lasts_two_weeks(self, auth):
        _, data = auth.new_session()
        assert abs(data["exp"] - (time.time() + SESSION_SECONDS)) < 5

    @pytest.mark.unit
    def test_changing_the_password_signs_everyone_out(self, auth):
        cookie, _ = auth.new_session()
        assert Auth("owner", hash_password("new password"), "s" * 32, "api-token-value").read_session(cookie) is None

    @pytest.mark.unit
    def test_changing_the_username_signs_everyone_out(self, auth):
        cookie, _ = auth.new_session()
        assert Auth("someone-else", hash_password("pw"), "s" * 32, "t").read_session(cookie) is None


class TestCsrf:
    @pytest.mark.unit
    def test_matching_token_passes(self, auth):
        _, session = auth.new_session()
        assert Auth.check_csrf(session, session["csrf"]) is True

    @pytest.mark.unit
    @pytest.mark.parametrize("supplied", [None, "", "wrong", "x" * 100])
    def test_anything_else_fails(self, auth, supplied):
        _, session = auth.new_session()
        assert Auth.check_csrf(session, supplied) is False

    @pytest.mark.unit
    def test_no_session_fails(self):
        assert Auth.check_csrf(None, "anything") is False


class TestApiToken:
    @pytest.mark.unit
    def test_accepts_the_bearer_token(self, auth):
        assert auth.check_api_token("Bearer api-token-value") is True
        assert auth.check_api_token("bearer api-token-value") is True

    @pytest.mark.unit
    @pytest.mark.parametrize("header", [None, "", "Bearer", "Bearer ", "Bearer wrong", "api-token-value", "Basic api-token-value",
                                        "Bearer api-token-value-extra", "Bearer api-token-valu"])
    def test_rejects_everything_else(self, auth, header):
        assert auth.check_api_token(header) is False


class TestLoginThrottle:
    @pytest.fixture
    def clock(self):
        state = {"t": 1000.0}
        return state

    @pytest.fixture
    def throttle(self, clock):
        return LoginThrottle(max_failures=3, window=60, clock=lambda: clock["t"])

    @pytest.mark.unit
    def test_allows_until_the_limit(self, throttle):
        for _ in range(2):
            throttle.record_failure("ip")
        assert throttle.retry_after("ip") == 0
        throttle.record_failure("ip")
        assert throttle.retry_after("ip") > 0

    @pytest.mark.unit
    def test_clients_are_tracked_separately(self, throttle):
        for _ in range(3):
            throttle.record_failure("attacker")
        assert throttle.retry_after("attacker") > 0
        assert throttle.retry_after("someone-else") == 0

    @pytest.mark.unit
    def test_lockout_expires(self, throttle, clock):
        for _ in range(3):
            throttle.record_failure("ip")
        clock["t"] += 61
        assert throttle.retry_after("ip") == 0

    @pytest.mark.unit
    def test_reports_roughly_the_time_left(self, throttle, clock):
        for _ in range(3):
            throttle.record_failure("ip")
        clock["t"] += 20
        assert 38 <= throttle.retry_after("ip") <= 42

    @pytest.mark.unit
    def test_success_clears_the_record(self, throttle):
        for _ in range(2):
            throttle.record_failure("ip")
        throttle.reset("ip")
        throttle.record_failure("ip")
        assert throttle.retry_after("ip") == 0

    @pytest.mark.unit
    def test_stale_failures_do_not_accumulate(self, throttle, clock):
        for _ in range(2):
            throttle.record_failure("ip")
        clock["t"] += 61
        throttle.record_failure("ip")
        assert throttle.retry_after("ip") == 0

    @pytest.mark.unit
    def test_memory_is_bounded_under_a_flood_of_clients(self):
        t = {"v": 0.0}
        throttle = LoginThrottle(window=10, clock=lambda: t["v"])
        for i in range(10_001):
            throttle.record_failure(f"ip-{i}")
        t["v"] += 11
        throttle.record_failure("one-more")
        assert len(throttle._failures) < 10


class TestAuthHoldsOnlyAHash:
    @pytest.mark.unit
    def test_the_password_is_not_kept_on_the_object(self):
        auth = Auth("owner", hash_password("a very secret password"), "s" * 32, "tok")
        assert "a very secret password" not in repr(vars(auth))

    @pytest.mark.unit
    def test_setting_the_same_password_again_still_signs_sessions_out(self):
        old = Auth("owner", hash_password("pw"), "s" * 32, "tok")
        cookie, _ = old.new_session()
        assert Auth("owner", hash_password("pw"), "s" * 32, "tok").read_session(cookie) is None  # new salt, new hash

    @pytest.mark.unit
    def test_a_wrong_username_still_does_the_password_work(self, monkeypatch):
        calls = []
        real = verify_password
        monkeypatch.setattr("blog_app.auth.verify_password", lambda *a: calls.append(a) or real(*a))
        Auth("owner", hash_password("pw"), "s" * 32, "t").check_login("someone-else", "pw")
        assert len(calls) == 1  # no early exit that would reveal whether the username exists

    @pytest.mark.unit
    def test_a_malformed_stored_hash_never_lets_anyone_in(self):
        auth = Auth("owner", "not-a-hash", "s" * 32, "t")
        assert auth.check_login("owner", "not-a-hash") is False
        assert auth.check_login("owner", "") is False
