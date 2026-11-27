"""How the blog finds its login credential at startup, and proof the password itself is never kept."""

import os

import pytest

from blog_app import passwords
from blog_app.app import BlogApp, MissingPassword
from blog_app.config import Settings
from blog_app.passwords import hash_password, password_file, verify_password, write_hash


def start(tmp_path, **overrides) -> BlogApp:
    return BlogApp(Settings(data_dir=tmp_path / "data", **overrides))


def every_byte_on_disk(folder) -> bytes:
    return b"".join(path.read_bytes() for path in folder.rglob("*") if path.is_file())


class TestResolvingTheCredential:
    @pytest.mark.unit
    def test_no_password_anywhere_is_an_error_that_says_what_to_do(self, tmp_path):
        with pytest.raises(MissingPassword, match="set-password"):
            start(tmp_path)

    @pytest.mark.unit
    def test_a_configured_password_is_hashed_and_labelled(self, tmp_path):
        app = start(tmp_path, password="chosen password")
        assert verify_password("chosen password", app.password_hash) and app.password_source == "BLOG_PASSWORD"

    @pytest.mark.unit
    def test_a_configured_password_gives_the_same_hash_after_a_restart_so_sessions_survive(self, tmp_path):
        first = start(tmp_path, password="chosen password")
        again = start(tmp_path, password="chosen password")
        assert first.password_hash == again.password_hash
        cookie, _ = first.auth.new_session()
        assert again.auth.read_session(cookie) is not None

    @pytest.mark.unit
    def test_but_two_installs_with_the_same_password_do_not_share_a_hash(self, tmp_path):
        one = BlogApp(Settings(data_dir=tmp_path / "one", password="same password"))
        two = BlogApp(Settings(data_dir=tmp_path / "two", password="same password"))
        assert one.password_hash != two.password_hash

    @pytest.mark.unit
    def test_a_different_configured_password_signs_sessions_out(self, tmp_path):
        cookie, _ = start(tmp_path, password="first password").auth.new_session()
        assert start(tmp_path, password="second password").auth.read_session(cookie) is None

    @pytest.mark.unit
    def test_a_configured_hash_is_used_as_given(self, tmp_path):
        app = start(tmp_path, password_hash=hash_password("from a hash"))
        assert verify_password("from a hash", app.password_hash) and app.password_source == "BLOG_PASSWORD_HASH"

    @pytest.mark.unit
    def test_a_configured_hash_beats_a_configured_plaintext_password(self, tmp_path):
        app = start(tmp_path, password="plain", password_hash=hash_password("hashed"))
        assert verify_password("hashed", app.password_hash) and not verify_password("plain", app.password_hash)

    @pytest.mark.unit
    def test_an_invalid_configured_hash_is_refused_with_instructions(self, tmp_path):
        with pytest.raises(ValueError, match="hash-password"):
            start(tmp_path, password_hash="not a hash")

    @pytest.mark.unit
    def test_the_stored_hash_file_is_used(self, tmp_path):
        (tmp_path / "data").mkdir()
        write_hash(password_file(tmp_path / "data"), hash_password("from the file"))
        app = start(tmp_path)
        assert verify_password("from the file", app.password_hash) and app.password_source.endswith("password_hash")

    @pytest.mark.unit
    def test_a_corrupted_hash_file_is_refused_with_instructions(self, tmp_path):
        (tmp_path / "data").mkdir()
        password_file(tmp_path / "data").write_text("garbage")
        with pytest.raises(ValueError, match="set-password"):
            start(tmp_path)

    @pytest.mark.unit
    def test_an_empty_hash_file_counts_as_no_password(self, tmp_path):
        (tmp_path / "data").mkdir()
        password_file(tmp_path / "data").write_text("\n")
        with pytest.raises(MissingPassword):
            start(tmp_path)


class TestUpgradingFromAnEarlierVersion:
    @pytest.fixture
    def old_install(self, tmp_path):
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "blog_password").write_text("my old plaintext password\n")
        return tmp_path

    @pytest.mark.unit
    def test_the_old_password_keeps_working_but_is_no_longer_stored_as_plaintext(self, old_install):
        app = start(old_install)
        assert verify_password("my old plaintext password", app.password_hash)
        assert app.removed_plaintext_password is True
        assert not (old_install / "data" / "blog_password").exists()
        assert b"my old plaintext password" not in every_byte_on_disk(old_install / "data")

    @pytest.mark.unit
    def test_it_only_happens_once(self, old_install):
        start(old_install)
        again = start(old_install)
        assert again.removed_plaintext_password is False
        assert verify_password("my old plaintext password", again.password_hash)

    @pytest.mark.unit
    def test_a_leftover_plaintext_file_is_removed_even_when_another_source_supplies_the_password(self, old_install):
        app = start(old_install, password="set elsewhere")
        assert not (old_install / "data" / "blog_password").exists()
        assert verify_password("set elsewhere", app.password_hash)


class TestThePasswordIsNeverStored:
    @pytest.mark.unit
    def test_a_configured_password_never_reaches_the_disk(self, tmp_path):
        start(tmp_path, password="distinctive-secret-9f3a")
        assert b"distinctive-secret-9f3a" not in every_byte_on_disk(tmp_path / "data")
        assert not password_file(tmp_path / "data").exists()  # nothing was even written for it

    @pytest.mark.unit
    def test_the_app_object_holds_no_copy_of_it(self, tmp_path):
        app = start(tmp_path, password="distinctive-secret-9f3a")
        assert "distinctive-secret-9f3a" not in repr(vars(app)) + repr(vars(app.auth))

    @pytest.mark.unit
    def test_the_stored_file_is_only_a_hash(self, tmp_path):
        (tmp_path / "data").mkdir()
        write_hash(password_file(tmp_path / "data"), hash_password("distinctive-secret-9f3a"))
        start(tmp_path)
        assert b"distinctive-secret-9f3a" not in every_byte_on_disk(tmp_path / "data")
        assert passwords.is_valid_hash(password_file(tmp_path / "data").read_text())

    @pytest.mark.unit
    @pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
    def test_no_file_in_the_data_folder_is_readable_by_others(self, tmp_path):
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "blog_password").write_text("old plaintext")
        start(tmp_path)
        for path in (tmp_path / "data").rglob("*"):
            if path.is_file():
                assert path.stat().st_mode & 0o077 == 0, path
