"""Tests for password hashing and the files that hold the hash."""

import base64
import os
import stat

import pytest

from blog_app import passwords
from blog_app.passwords import (
    DEFAULT_ITERATIONS, generate_password, hash_password, is_valid_hash, migrate_legacy_password, password_file, read_hash,
    stable_salt, verify_password, write_hash,
)


class TestHashing:
    @pytest.mark.unit
    def test_the_real_work_factor_meets_current_guidance(self):
        assert DEFAULT_ITERATIONS >= 600_000  # OWASP's figure for PBKDF2-HMAC-SHA256

    @pytest.mark.unit
    def test_format(self):
        scheme, iterations, salt, digest = hash_password("secret").split("$")
        assert scheme == "pbkdf2_sha256" and int(iterations) == passwords.ITERATIONS
        assert len(base64.b64decode(salt)) == 16 and len(base64.b64decode(digest)) == 32

    @pytest.mark.unit
    def test_the_hash_does_not_contain_the_password(self):
        assert "correct horse" not in hash_password("correct horse battery staple")

    @pytest.mark.unit
    def test_every_hash_has_its_own_salt(self):
        assert hash_password("same") != hash_password("same")
        assert verify_password("same", hash_password("same"))

    @pytest.mark.unit
    @pytest.mark.parametrize("password", ["pw", "with space ", "pässwörd-日本-🎉", "x" * 10_000, "a:b$c"])
    def test_round_trip(self, password):
        assert verify_password(password, hash_password(password)) is True

    @pytest.mark.unit
    @pytest.mark.parametrize("wrong", ["", "PW", "pw ", " pw", "pw\n", "p", "pww"])
    def test_wrong_passwords_are_refused(self, wrong):
        assert verify_password(wrong, hash_password("pw")) is False

    @pytest.mark.unit
    def test_verification_uses_the_iterations_stored_in_the_hash_not_the_current_setting(self):
        old = hash_password("pw", iterations=5)
        assert old.split("$")[1] == "5" and verify_password("pw", old) is True
        assert verify_password("pw", hash_password("pw", iterations=7)) is True

    @pytest.mark.unit
    @pytest.mark.parametrize("bad", [
        "", "plain text", "pbkdf2_sha256", "pbkdf2_sha256$1000$salt", "pbkdf2_sha256$1000$salt$hash$extra",
        "md5$1000$c2FsdA==$aGFzaA==", "pbkdf2_sha256$abc$c2FsdA==$aGFzaA==", "pbkdf2_sha256$0$c2FsdA==$aGFzaA==",
        "pbkdf2_sha256$-5$c2FsdA==$aGFzaA==", "pbkdf2_sha256$1000$!!!$aGFzaA==", "pbkdf2_sha256$1000$c2FsdA==$!!!",
        "pbkdf2_sha256$1000$$aGFzaA==", "pbkdf2_sha256$1000$c2FsdA==$", "pbkdf2_sha256$99999999999$c2FsdA==$aGFzaA==",
    ])
    def test_malformed_hashes_are_invalid_and_never_match(self, bad):
        assert is_valid_hash(bad) is False
        assert verify_password("anything", bad) is False
        assert verify_password("", bad) is False

    @pytest.mark.unit
    def test_a_well_formed_hash_is_valid(self):
        assert is_valid_hash(hash_password("x")) is True
        assert is_valid_hash("  " + hash_password("x") + "\n") is True

    @pytest.mark.unit
    def test_a_tampered_hash_no_longer_matches(self):
        scheme, iterations, salt, digest = hash_password("pw").split("$")
        flipped = base64.b64encode(bytes([base64.b64decode(digest)[0] ^ 1]) + base64.b64decode(digest)[1:]).decode()
        assert verify_password("pw", "$".join([scheme, iterations, salt, flipped])) is False


class TestGeneratedPasswords:
    @pytest.mark.unit
    def test_long_and_random(self):
        assert len({generate_password() for _ in range(50)}) == 50
        assert all(len(generate_password()) >= 24 for _ in range(5))

    @pytest.mark.unit
    def test_safe_to_type_and_to_put_in_a_url(self):
        assert all(c.isalnum() or c in "-_" for c in generate_password())


class TestHashFile:
    @pytest.mark.unit
    def test_missing_or_empty_means_none(self, tmp_path):
        assert read_hash(tmp_path / "password_hash") is None
        (tmp_path / "password_hash").write_text("\n")
        assert read_hash(tmp_path / "password_hash") is None

    @pytest.mark.unit
    def test_write_then_read(self, tmp_path):
        encoded = hash_password("pw")
        write_hash(tmp_path / "password_hash", encoded)
        assert read_hash(tmp_path / "password_hash") == encoded

    @pytest.mark.unit
    @pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
    def test_owner_only_even_if_the_file_already_existed(self, tmp_path):
        path = tmp_path / "password_hash"
        path.write_text("old")
        os.chmod(path, 0o640)
        write_hash(path, hash_password("pw"))
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o600

    @pytest.mark.unit
    def test_overwriting_replaces_the_old_hash_completely(self, tmp_path):
        path = tmp_path / "password_hash"
        write_hash(path, hash_password("a-much-longer-first-password-" * 5))
        write_hash(path, hash_password("b"))
        assert verify_password("b", read_hash(path)) and path.read_text().count("pbkdf2_sha256") == 1

    @pytest.mark.unit
    def test_location(self, tmp_path):
        assert password_file(tmp_path) == tmp_path / "password_hash"


class TestMigratingAnOldPlaintextFile:
    @pytest.mark.unit
    def test_plaintext_becomes_a_hash_and_the_plaintext_is_deleted(self, tmp_path):
        (tmp_path / "blog_password").write_text("old plaintext password\n")
        assert migrate_legacy_password(tmp_path) is True
        assert not (tmp_path / "blog_password").exists()
        assert verify_password("old plaintext password", read_hash(password_file(tmp_path)))
        assert b"old plaintext password" not in (tmp_path / "password_hash").read_bytes()

    @pytest.mark.unit
    @pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
    def test_the_new_file_is_owner_only(self, tmp_path):
        (tmp_path / "blog_password").write_text("pw-long-enough")
        migrate_legacy_password(tmp_path)
        assert stat.S_IMODE(os.stat(tmp_path / "password_hash").st_mode) == 0o600

    @pytest.mark.unit
    def test_an_existing_hash_is_never_overwritten(self, tmp_path):
        existing = hash_password("current password")
        write_hash(password_file(tmp_path), existing)
        (tmp_path / "blog_password").write_text("stale old password")
        assert migrate_legacy_password(tmp_path) is True
        assert read_hash(password_file(tmp_path)) == existing
        assert not (tmp_path / "blog_password").exists()  # the stale plaintext is still removed

    @pytest.mark.unit
    def test_an_empty_plaintext_file_is_removed_and_makes_no_hash(self, tmp_path):
        (tmp_path / "blog_password").write_text("\n")
        assert migrate_legacy_password(tmp_path) is True
        assert not (tmp_path / "blog_password").exists() and read_hash(password_file(tmp_path)) is None

    @pytest.mark.unit
    def test_nothing_to_migrate(self, tmp_path):
        assert migrate_legacy_password(tmp_path) is False
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.unit
    def test_running_it_twice_is_harmless(self, tmp_path):
        (tmp_path / "blog_password").write_text("pw-long-enough")
        assert migrate_legacy_password(tmp_path) is True
        assert migrate_legacy_password(tmp_path) is False
        assert verify_password("pw-long-enough", read_hash(password_file(tmp_path)))


class TestStableSalt:
    @pytest.mark.unit
    def test_the_same_inputs_give_the_same_hash(self):
        salt = stable_salt("install-key", "pw")
        assert hash_password("pw", salt=salt) == hash_password("pw", salt=salt)
        assert verify_password("pw", hash_password("pw", salt=salt))

    @pytest.mark.unit
    def test_it_differs_per_install_and_per_password(self):
        assert stable_salt("key-a", "pw") != stable_salt("key-b", "pw")
        assert stable_salt("key-a", "pw") != stable_salt("key-a", "other")
        assert len(stable_salt("key-a", "pw")) == passwords.SALT_BYTES

    @pytest.mark.unit
    def test_the_salt_does_not_reveal_the_password(self):
        assert b"distinctive-secret" not in stable_salt("key", "distinctive-secret")
