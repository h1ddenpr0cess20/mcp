"""Tests for settings and the secrets the blog keeps on disk."""

import os
import stat

import pytest

import blog as entry
from blog_app.app import BlogApp
from blog_app.config import Settings, load_or_create_secret


class TestSecrets:
    @pytest.mark.unit
    def test_creates_and_reuses(self, tmp_path):
        first = load_or_create_secret(tmp_path / "s")
        assert len(first) >= 20
        assert load_or_create_secret(tmp_path / "s") == first
        assert (tmp_path / "s").read_text().strip() == first

    @pytest.mark.unit
    @pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
    def test_owner_only(self, tmp_path):
        load_or_create_secret(tmp_path / "s")
        assert stat.S_IMODE(os.stat(tmp_path / "s").st_mode) == 0o600

    @pytest.mark.unit
    @pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
    def test_tightens_a_pre_existing_empty_file(self, tmp_path):
        (tmp_path / "s").write_text("")
        os.chmod(tmp_path / "s", 0o644)
        load_or_create_secret(tmp_path / "s")
        assert stat.S_IMODE(os.stat(tmp_path / "s").st_mode) == 0o600

    @pytest.mark.unit
    def test_secrets_are_distinct(self, tmp_path):
        assert load_or_create_secret(tmp_path / "a") != load_or_create_secret(tmp_path / "b")


class TestSettings:
    @pytest.mark.unit
    def test_defaults(self, tmp_path):
        s = Settings(data_dir=tmp_path)
        assert (s.host, s.port, s.username, s.title, s.public) == ("127.0.0.1", 9901, "owner", "Private Blog", False)

    @pytest.mark.unit
    @pytest.mark.parametrize("username", ["", "a:b"])
    def test_bad_usernames(self, tmp_path, username):
        with pytest.raises(ValueError, match="BLOG_USERNAME"):
            Settings(data_dir=tmp_path, username=username)

    @pytest.mark.unit
    def test_tls_files_come_as_a_pair(self, tmp_path):
        with pytest.raises(ValueError, match="together"):
            Settings(data_dir=tmp_path, tls_cert="c.pem")
        with pytest.raises(ValueError, match="together"):
            Settings(data_dir=tmp_path, tls_key="k.pem")

    @pytest.mark.unit
    def test_paths_expand_the_home_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        s = Settings(data_dir="~/blog", tls_cert="~/c.pem", tls_key="~/k.pem")
        assert str(s.data_dir) == str(tmp_path / "blog")
        assert s.tls_cert == str(tmp_path / "c.pem")

    @pytest.mark.unit
    def test_public_url_loses_its_trailing_slash(self, tmp_path):
        assert Settings(data_dir=tmp_path, public_url="https://blog.example.com/").public_url == "https://blog.example.com"

    @pytest.mark.unit
    def test_from_env(self, tmp_path, monkeypatch):
        for name, value in {"BLOG_DIR": str(tmp_path), "BLOG_HOST": "0.0.0.0", "BLOG_PORT": "1234", "BLOG_TITLE": "T",
                            "BLOG_DESCRIPTION": "D", "BLOG_USERNAME": "me", "BLOG_PASSWORD": "pw", "BLOG_PUBLIC": "true",
                            "BLOG_PUBLIC_URL": "https://x.example/", "BLOG_API_TOKEN": "tok"}.items():
            monkeypatch.setenv(name, value)
        s = Settings.from_env()
        assert (s.host, s.port, s.title, s.description, s.username, s.password, s.public, s.public_url, s.api_token) == (
            "0.0.0.0", 1234, "T", "D", "me", "pw", True, "https://x.example", "tok")

    @pytest.mark.unit
    @pytest.mark.parametrize("value,expected", [("true", True), ("1", True), ("YES", True), ("on", True),
                                                ("false", False), ("0", False), ("", False), ("nope", False)])
    def test_public_flag_parsing(self, tmp_path, monkeypatch, value, expected):
        monkeypatch.setenv("BLOG_DIR", str(tmp_path))
        monkeypatch.setenv("BLOG_PUBLIC", value)
        assert Settings.from_env().public is expected

    @pytest.mark.unit
    def test_private_is_the_default(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BLOG_DIR", str(tmp_path))
        monkeypatch.delenv("BLOG_PUBLIC", raising=False)
        assert Settings.from_env().public is False


class TestFirstRunCredentials:
    """The first start generates the password; the startup message must tell the person how to log in."""

    @pytest.fixture
    def start(self, tmp_path):
        """Start the blog's app on `tmp_path` and return (settings, app). Calling it again is a restart."""

        def build(**overrides):
            settings = Settings(data_dir=tmp_path / "data", **overrides)
            return settings, BlogApp(settings)

        return build

    @staticmethod
    def message(settings, app, interactive):
        return "\n".join(entry.startup_lines(settings, app, interactive))

    @pytest.mark.unit
    def test_the_first_start_generates_and_flags_the_password_as_new(self, start):
        _, app = start()
        assert app.password_is_new is True and len(app.password) >= 20

    @pytest.mark.unit
    def test_later_starts_reuse_it_and_do_not_flag_it(self, start):
        _, first = start()
        _, second = start()
        assert second.password_is_new is False and second.password == first.password

    @pytest.mark.unit
    def test_a_configured_password_is_never_new(self, start):
        _, app = start(password="chosen")
        assert app.password_is_new is False and app.password == "chosen"

    @pytest.mark.unit
    def test_an_empty_password_file_counts_as_missing(self, start, tmp_path):
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "blog_password").write_text("\n")
        assert start()[1].password_is_new is True

    @pytest.mark.unit
    def test_an_interactive_first_run_prints_the_password_once(self, start):
        settings, app = start()
        first = self.message(settings, app, interactive=True)
        assert f"password: {app.password}" in first and "username: owner" in first and "only printed this once" in first
        settings, restarted = start()
        later = self.message(settings, restarted, interactive=True)
        assert restarted.password not in later and "blog_password" in later

    @pytest.mark.unit
    def test_a_non_interactive_start_never_prints_the_password(self, start):
        settings, app = start()
        assert app.password not in self.message(settings, app, interactive=False)

    @pytest.mark.unit
    def test_a_configured_password_is_named_but_not_shown(self, start):
        settings, app = start(password="chosen")
        text = self.message(settings, app, interactive=True)
        assert "chosen" not in text and "set in BLOG_PASSWORD" in text

    @pytest.mark.unit
    def test_a_password_file_is_called_a_file_not_the_password(self, start):
        start()
        settings, restarted = start()
        assert "The password is stored in the file" in self.message(settings, restarted, interactive=False)

    @pytest.mark.unit
    def test_the_api_token_source_is_stated(self, start):
        settings, app = start()
        assert "API token in the file" in self.message(settings, app, interactive=False)
        settings, app = start(api_token="tok")
        assert "set in BLOG_API_TOKEN" in self.message(settings, app, interactive=False)

    @pytest.mark.unit
    def test_warns_about_plain_http_off_loopback(self, start):
        settings, app = start(host="0.0.0.0")
        assert "without TLS" in self.message(settings, app, interactive=False)
