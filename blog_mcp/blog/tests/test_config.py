"""Tests for settings and the secrets the blog keeps on disk."""

import os
import stat

import pytest

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
        os.chmod(tmp_path / "s", 0o640)
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
        assert s.allowed_hosts == ["127.0.0.1", "localhost"]

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
    def test_allowed_hosts_cannot_be_empty(self, tmp_path):
        with pytest.raises(ValueError, match="BLOG_ALLOWED_HOSTS"):
            Settings(data_dir=tmp_path, allowed_hosts=[])

    @pytest.mark.unit
    def test_from_env(self, tmp_path, monkeypatch):
        for name, value in {"BLOG_DIR": str(tmp_path), "BLOG_HOST": "0.0.0.0", "BLOG_PORT": "1234", "BLOG_TITLE": "T",
                            "BLOG_DESCRIPTION": "D", "BLOG_USERNAME": "me", "BLOG_PASSWORD": "pw", "BLOG_PUBLIC": "true",
                            "BLOG_PUBLIC_URL": "https://x.example/", "BLOG_ALLOWED_HOSTS": "blog.example.com, localhost",
                            "BLOG_API_TOKEN": "tok", "BLOG_PASSWORD_HASH": "h"}.items():
            monkeypatch.setenv(name, value)
        s = Settings.from_env()
        assert (s.host, s.port, s.title, s.description, s.username, s.password, s.public, s.public_url, s.api_token) == (
            "0.0.0.0", 1234, "T", "D", "me", "pw", True, "https://x.example", "tok")
        assert s.password_hash == "h"
        assert s.allowed_hosts == ["blog.example.com", "localhost"]

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
