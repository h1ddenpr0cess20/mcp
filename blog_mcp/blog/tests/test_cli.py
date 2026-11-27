"""Tests for blog.py's commands: starting for the first time, set-password, and hash-password."""

import io
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

import blog as entry
from blog_app import Settings, passwords
from blog_app.passwords import password_file, read_hash, verify_password

BLOG_PY = Path(__file__).resolve().parent.parent / "blog.py"


def typed(*answers):
    """A stand-in for getpass that 'types' the given answers in order."""
    queue = list(answers)
    return lambda prompt: queue.pop(0)


def on_disk(folder) -> bytes:
    return b"".join(p.read_bytes() for p in Path(folder).rglob("*") if p.is_file())


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "data")


class TestSetPassword:
    @pytest.mark.unit
    def test_typed_password_is_stored_as_a_hash(self, settings):
        out = io.StringIO()
        assert entry.set_password(settings, ask=typed("my new password", "my new password"), out=out) == 0
        assert verify_password("my new password", read_hash(password_file(settings.data_dir)))
        assert b"my new password" not in on_disk(settings.data_dir)
        assert "my new password" not in out.getvalue() and "Restart" in out.getvalue()

    @pytest.mark.unit
    def test_mismatched_entries_change_nothing(self, settings):
        out = io.StringIO()
        assert entry.set_password(settings, ask=typed("first password", "different"), out=out) == 1
        assert read_hash(password_file(settings.data_dir)) is None and "did not match" in out.getvalue()

    @pytest.mark.unit
    @pytest.mark.parametrize("short", ["", "a", "1234567"])
    def test_too_short_is_refused(self, settings, short):
        out = io.StringIO()
        assert entry.set_password(settings, ask=typed(short), out=out) == 1
        assert read_hash(password_file(settings.data_dir)) is None and "too short" in out.getvalue()

    @pytest.mark.unit
    def test_exactly_the_minimum_length_is_accepted(self, settings):
        assert entry.set_password(settings, ask=typed("12345678", "12345678"), out=io.StringIO()) == 0

    @pytest.mark.unit
    def test_generate_shows_the_password_once_and_stores_only_a_hash(self, settings):
        out = io.StringIO()
        assert entry.set_password(settings, generate=True, out=out) == 0
        shown = [line.split(": ", 1)[1] for line in out.getvalue().splitlines() if "new password is:" in line][0]
        assert verify_password(shown, read_hash(password_file(settings.data_dir)))
        assert shown.encode() not in on_disk(settings.data_dir)
        assert out.getvalue().count(shown) == 1

    @pytest.mark.unit
    def test_changing_an_existing_password_replaces_it(self, settings):
        entry.set_password(settings, ask=typed("first password", "first password"), out=io.StringIO())
        entry.set_password(settings, ask=typed("second password", "second password"), out=io.StringIO())
        stored = read_hash(password_file(settings.data_dir))
        assert verify_password("second password", stored) and not verify_password("first password", stored)

    @pytest.mark.unit
    def test_it_removes_an_old_plaintext_file(self, settings):
        settings.data_dir.mkdir(parents=True)
        (settings.data_dir / "blog_password").write_text("old plaintext")
        entry.set_password(settings, generate=True, out=io.StringIO())
        assert not (settings.data_dir / "blog_password").exists() and b"old plaintext" not in on_disk(settings.data_dir)

    @pytest.mark.unit
    def test_it_warns_when_a_configured_password_would_override_it(self, tmp_path):
        out = io.StringIO()
        entry.set_password(Settings(data_dir=tmp_path / "d", password="from env"), generate=True, out=out)
        assert "takes priority" in out.getvalue()

    @pytest.mark.unit
    @pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
    def test_a_brand_new_blog_gets_an_owner_only_folder(self, settings):
        entry.set_password(settings, generate=True, out=io.StringIO())
        assert oct(settings.data_dir.stat().st_mode & 0o777) == "0o700"
        assert oct(password_file(settings.data_dir).stat().st_mode & 0o777) == "0o600"


class TestHashPassword:
    @pytest.mark.unit
    def test_prints_a_hash_to_stdout_and_nothing_secret_elsewhere(self):
        out, stdout = io.StringIO(), io.StringIO()
        assert entry.hash_password_command(ask=typed("a typed password", "a typed password"), out=out, stdout=stdout) == 0
        line = stdout.getvalue().strip()
        assert verify_password("a typed password", line) and passwords.is_valid_hash(line)
        assert "a typed password" not in out.getvalue() + stdout.getvalue()
        assert "BLOG_PASSWORD_HASH" in out.getvalue()

    @pytest.mark.unit
    @pytest.mark.parametrize("answers", [("short",), ("a long enough one", "but different")])
    def test_bad_input_prints_no_hash(self, answers):
        stdout = io.StringIO()
        assert entry.hash_password_command(ask=typed(*answers), out=io.StringIO(), stdout=stdout) == 1
        assert stdout.getvalue() == ""


class TestStartingTheBlog:
    @pytest.fixture(autouse=True)
    def no_server(self, monkeypatch):
        launched = []
        monkeypatch.setattr(entry.uvicorn, "run", lambda app, **kw: launched.append(kw))
        self.launched = launched

    @pytest.mark.unit
    def test_a_first_start_from_a_terminal_makes_a_password_and_shows_it_once(self, settings):
        out = io.StringIO()
        assert entry.run(settings, interactive=True, out=out) == 0
        shown = [line.split("password: ", 1)[1] for line in out.getvalue().splitlines() if line.startswith("[blog]     password: ")][0]
        assert out.getvalue().count(shown) == 1 and len(shown) >= 24
        assert verify_password(shown, read_hash(password_file(settings.data_dir)))
        assert shown.encode() not in on_disk(settings.data_dir)
        assert "only a hash is stored" in out.getvalue() and entry._SET_PASSWORD in out.getvalue()
        assert len(self.launched) == 1

    @pytest.mark.unit
    def test_the_next_start_shows_no_password(self, settings):
        entry.run(settings, interactive=True, out=io.StringIO())
        shown = io.StringIO()
        assert entry.run(settings, interactive=True, out=shown) == 0
        assert "password:" not in shown.getvalue().replace("the password from", "")
        assert "Forgotten the password?" in shown.getvalue() and entry._SET_PASSWORD in shown.getvalue()

    @pytest.mark.unit
    def test_without_a_terminal_and_without_a_password_it_refuses_to_start(self, settings):
        out = io.StringIO()
        assert entry.run(settings, interactive=False, out=out) == 2
        assert "set-password" in out.getvalue() and self.launched == []
        assert read_hash(password_file(settings.data_dir)) is None  # nothing was generated that nobody could see

    @pytest.mark.unit
    def test_a_configured_password_is_named_never_shown(self, tmp_path):
        out = io.StringIO()
        entry.run(Settings(data_dir=tmp_path / "d", password="from the environment"), interactive=True, out=out)
        assert "from the environment" not in out.getvalue() and "BLOG_PASSWORD" in out.getvalue()
        assert read_hash(password_file(tmp_path / "d")) is None

    @pytest.mark.unit
    def test_an_upgrade_says_the_plaintext_file_was_removed(self, settings):
        settings.data_dir.mkdir(parents=True)
        (settings.data_dir / "blog_password").write_text("old plaintext password")
        out = io.StringIO()
        entry.run(settings, interactive=True, out=out)
        assert "plain text" in out.getvalue() and "old plaintext password" not in out.getvalue()
        assert not (settings.data_dir / "blog_password").exists()

    @pytest.mark.unit
    def test_warns_about_plain_http_off_loopback(self, tmp_path):
        out = io.StringIO()
        entry.run(Settings(data_dir=tmp_path / "d", password="long enough", host="0.0.0.0"), interactive=False, out=out)
        assert "without TLS" in out.getvalue()


class TestTheRealProgram:
    """Run blog.py as a separate process, exactly as a person would."""

    @staticmethod
    def run(*args, env_extra=None, **kwargs):
        env = {**os.environ, **(env_extra or {})}
        env.pop("BLOG_PASSWORD", None)
        env.pop("BLOG_PASSWORD_HASH", None)
        return subprocess.run([sys.executable, str(BLOG_PY), *args], capture_output=True, text=True, env=env, timeout=60, **kwargs)

    @pytest.mark.integration
    def test_set_password_then_log_in_with_it_and_find_no_plaintext_anywhere(self, tmp_path):
        data = tmp_path / "data"
        result = self.run("set-password", "--generate", env_extra={"BLOG_DIR": str(data)})
        assert result.returncode == 0
        password = [line.split(": ", 1)[1] for line in result.stderr.splitlines() if "new password is:" in line][0]
        assert password.encode() not in on_disk(data) and password not in result.stdout

        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        environment = {**os.environ, "BLOG_DIR": str(data), "BLOG_PORT": str(port), "BLOG_PASSWORD": "", "BLOG_PASSWORD_HASH": ""}
        server = subprocess.Popen([sys.executable, str(BLOG_PY)], env=environment,
                                  stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        try:
            import http.client
            import time
            from urllib.parse import urlencode

            for _ in range(100):
                try:
                    http.client.HTTPConnection("127.0.0.1", port, timeout=1).request("GET", "/healthz")
                    break
                except OSError:
                    time.sleep(0.1)

            def login(pw):
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                conn.request("POST", "/login", body=urlencode({"username": "owner", "password": pw}),
                             headers={"Content-Type": "application/x-www-form-urlencoded"})
                response = conn.getresponse()
                response.read()
                return response.status

            assert login(password) == 303 and login("not the password") == 401
            assert password.encode() not in on_disk(data)  # still nowhere on disk after logging in
        finally:
            server.terminate()
            server.wait(timeout=10)

    @pytest.mark.integration
    def test_starting_with_no_password_and_no_terminal_exits_with_instructions(self, tmp_path):
        result = self.run(env_extra={"BLOG_DIR": str(tmp_path / "data"), "BLOG_PORT": "0"})
        assert result.returncode == 2 and "set-password" in result.stderr
        assert read_hash(password_file(tmp_path / "data")) is None

    @pytest.mark.integration
    def test_hash_password_prints_a_hash_that_works_as_blog_password_hash(self, tmp_path):
        result = subprocess.run([sys.executable, "-c", (
            "import sys; sys.path.insert(0, %r); import blog; "
            "sys.exit(blog.hash_password_command(ask=lambda prompt: 'a typed password'))") % str(BLOG_PY.parent)],
            capture_output=True, text=True, timeout=60)
        assert result.returncode == 0
        encoded = result.stdout.strip()
        assert verify_password("a typed password", encoded) and "a typed password" not in result.stdout + result.stderr
        from blog_app import create_app

        app = create_app(Settings(data_dir=tmp_path / "data", password_hash=encoded))
        assert verify_password("a typed password", app.state.blog.password_hash)
