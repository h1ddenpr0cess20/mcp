"""Tests for attachment file handling (names, text detection, safe storage) and the attachment records."""

import asyncio
import hashlib
import os
import stat
import time

import pytest

from blog_app import BlogStore, NotFound
from blog_app.attachments import AttachmentFiles, clean_filename, guess_content_type, looks_like_text
from blog_app.store import MAX_ATTACHMENTS_PER_POST, BlogError, TooLarge


class FakeUpload:
    """What Starlette's UploadFile offers the code under test: an async read(size)."""

    def __init__(self, data: bytes):
        self._data, self._at = data, 0

    async def read(self, size: int = -1) -> bytes:
        chunk = self._data[self._at:] if size < 0 else self._data[self._at:self._at + size]
        self._at += len(chunk)
        return chunk


def receive(files, data: bytes):
    return asyncio.run(files.receive(FakeUpload(data)))


class TestCleanFilename:
    @pytest.mark.unit
    @pytest.mark.parametrize("raw,expected", [
        ("report.pdf", "report.pdf"),
        ("analysis.py", "analysis.py"),
        (".gitignore", ".gitignore"),
        ("my file (final) v2.tar.gz", "my file (final) v2.tar.gz"),
        ("日本語のファイル.txt", "日本語のファイル.txt"),
        ("../../etc/passwd", "passwd"),
        ("/etc/shadow", "shadow"),
        ("C:\\Windows\\System32\\cmd.exe", "cmd.exe"),
        ("a/b\\c/d.txt", "d.txt"),
        ("..", "file"), (".", "file"), ("", "file"), ("   ", "file"), ("/", "file"), ("dir/", "file"),
        ("name\r\nSet-Cookie: x=1.txt", "nameSet-Cookie: x=1.txt"),
        ("tab\tseparated\x00null.txt", "tabseparatednull.txt"),
        ("  padded   with   spaces.txt  ", "padded with spaces.txt"),
    ])
    def test_cleaning(self, raw, expected):
        assert clean_filename(raw) == expected

    @pytest.mark.unit
    @pytest.mark.parametrize("trick", ["invoice\u202egpj.exe", "a\u200bb.txt", "x\u2066y.txt", "z\ufeff.txt", "soft\u00adhyphen.txt"])
    def test_invisible_and_text_reordering_characters_are_removed(self, trick):
        cleaned = clean_filename(trick)
        assert all(ch.isprintable() and ch not in "\u202e\u200b\u2066\ufeff\u00ad" for ch in cleaned)

    @pytest.mark.unit
    def test_the_right_to_left_override_trick_does_not_survive(self):
        assert clean_filename("photo\u202egpj.exe") == "photogpj.exe"  # reads as it is written, with the .exe visible

    @pytest.mark.unit
    def test_long_names_are_shortened_but_keep_their_extension(self):
        cleaned = clean_filename("x" * 500 + ".tar.gz")
        assert len(cleaned) <= 150 and cleaned.endswith(".gz")
        assert len(clean_filename("y" * 500)) == 150

    @pytest.mark.unit
    def test_never_returns_a_path(self):
        for raw in ("../x", "..\\x", "a/../../b", "%2e%2e/x", "....//x"):
            assert "/" not in clean_filename(raw) and "\\" not in clean_filename(raw)

    @pytest.mark.unit
    def test_none_and_non_strings_do_not_crash(self):
        assert clean_filename(None) == "file" and clean_filename(12345) == "12345"


class TestContentTypeAndText:
    @pytest.mark.unit
    @pytest.mark.parametrize("name,expected", [("a.py", "text/x-python"), ("a.csv", "text/csv"), ("a.pdf", "application/pdf"),
                                               ("a.json", "application/json"), ("noextension", "application/octet-stream"),
                                               ("a.unknownext", "application/octet-stream")])
    def test_guess(self, name, expected):
        assert guess_content_type(name) == expected

    @pytest.mark.unit
    @pytest.mark.parametrize("head", [b"", b"print('hello')\n", "naïve café 日本語".encode(), b"\xff"[:0], "x".encode() * 10_000])
    def test_text(self, head):
        assert looks_like_text(head) is True

    @pytest.mark.unit
    @pytest.mark.parametrize("head", [
        b"\x00\x01\x02", b"MZ\x90\x00\x03", b"PK\x03\x04\x00\x00", b"text then \x00 a null", b"\xff\xfe\xfd binary",
    ])
    def test_binary(self, head):
        assert looks_like_text(head) is False

    @pytest.mark.unit
    def test_a_file_cut_off_in_the_middle_of_a_character_still_counts_as_text(self):
        assert looks_like_text(("日本語" * 10).encode()[:-1]) is True

    @pytest.mark.unit
    def test_invalid_bytes_in_the_middle_are_not_text(self):
        assert looks_like_text(b"fine \xff\xfe in the middle and then plenty more text after it") is False


class TestAttachmentFiles:
    @pytest.fixture
    def files(self, tmp_path):
        return AttachmentFiles(tmp_path / "attachments", max_bytes=1024 * 1024)

    @pytest.mark.unit
    def test_receives_and_describes_a_file(self, files):
        got = receive(files, b"print('hi')\n")
        assert (got.size, got.is_text, got.sha256) == (12, True, hashlib.sha256(b"print('hi')\n").hexdigest())
        assert got.path.read_bytes() == b"print('hi')\n"

    @pytest.mark.unit
    def test_binary_is_recognised(self, files):
        assert receive(files, b"\x89PNG\x00\x00binary").is_text is False

    @pytest.mark.unit
    def test_an_empty_file_is_allowed(self, files):  # an empty __init__.py is a perfectly good attachment
        got = receive(files, b"")
        assert got.size == 0 and got.sha256 == hashlib.sha256(b"").hexdigest()

    @pytest.mark.unit
    def test_exactly_the_limit_is_accepted_and_one_byte_more_is_not(self, files):
        assert receive(files, b"x" * files.max_bytes).size == files.max_bytes
        with pytest.raises(TooLarge, match="at most 1 MB"):
            receive(files, b"x" * (files.max_bytes + 1))

    @pytest.mark.unit
    def test_a_rejected_upload_leaves_nothing_behind(self, files):
        with pytest.raises(TooLarge):
            receive(files, b"x" * (files.max_bytes + 1))
        assert list(files.directory.iterdir()) == []

    @pytest.mark.unit
    def test_it_stops_reading_once_the_limit_is_passed(self, files):
        upload = FakeUpload(b"x" * (50 * 1024 * 1024))
        with pytest.raises(TooLarge):
            asyncio.run(files.receive(upload))
        assert upload._at <= files.max_bytes + 1024 * 1024  # never read the other ~49 MB

    @pytest.mark.unit
    def test_a_failure_while_reading_cleans_up(self, files):
        class Broken:
            async def read(self, size=-1):
                raise ConnectionError("client went away")

        with pytest.raises(ConnectionError):
            asyncio.run(files.receive(Broken()))
        assert list(files.directory.iterdir()) == []

    @pytest.mark.unit
    @pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
    def test_files_are_owner_only_under_their_id_with_no_extension(self, files):
        files.commit(receive(files, b"data"), "a" * 32)
        stored = files.path("a" * 32)
        assert stored.name == "a" * 32 and stored.suffix == "" and stat.S_IMODE(stored.stat().st_mode) == 0o600

    @pytest.mark.unit
    def test_committing_replaces_the_previous_file(self, files):
        files.commit(receive(files, b"first"), "b" * 32)
        files.commit(receive(files, b"second"), "b" * 32)
        assert files.path("b" * 32).read_bytes() == b"second" and len(list(files.directory.iterdir())) == 1

    @pytest.mark.unit
    @pytest.mark.parametrize("bad", [
        "", "../x", "..", "a" * 31, "a" * 33, "A" * 32, "g" * 32, "a" * 32 + "/../x", "/etc/passwd", "a" * 32 + "\n",
    ])
    def test_ids_that_are_not_ours_never_become_paths(self, files, bad):
        with pytest.raises(NotFound):
            files.path(bad)

    @pytest.mark.unit
    def test_remove(self, files):
        files.commit(receive(files, b"x"), "c" * 32)
        files.remove("c" * 32)
        assert not files.path("c" * 32).exists()
        files.remove("c" * 32)  # removing twice is harmless

    @pytest.mark.unit
    def test_discard(self, files):
        got = receive(files, b"x")
        files.discard(got)
        assert not got.path.exists()

    @pytest.mark.unit
    def test_reading_text(self, files):
        files.commit(receive(files, "héllo\nworld".encode()), "d" * 32)
        assert files.read_text("d" * 32) == ("héllo\nworld", False)

    @pytest.mark.unit
    def test_reading_a_long_text_file_is_cut_short_and_says_so(self, files):
        files.commit(receive(files, b"x" * 1000), "e" * 32)
        assert files.read_text("e" * 32, limit=100) == ("x" * 100, True)

    @pytest.mark.unit
    def test_reading_never_fails_on_odd_bytes(self, files):
        files.commit(receive(files, b"ok \xff\xfe still ok"), "f" * 32)
        assert files.read_text("f" * 32)[0].startswith("ok ")

    @pytest.mark.unit
    def test_old_partial_uploads_are_swept_up_and_fresh_ones_are_kept(self, tmp_path):
        folder = tmp_path / "attachments"
        folder.mkdir()
        old, fresh, real = folder / ".incoming-old", folder / ".incoming-fresh", folder / ("a" * 32)
        for path in (old, fresh, real):
            path.write_bytes(b"x")
        long_ago = time.time() - 7200
        os.utime(old, (long_ago, long_ago))
        AttachmentFiles(folder, 1024)
        assert not old.exists() and fresh.exists() and real.exists()


class TestAttachmentRecords:
    @pytest.fixture
    def post(self, blog):
        blog.create_post("Host post", "body", publish=True)
        return "host-post"

    @staticmethod
    def attach(blog, slug, name, size=10, text=True, attachment_id=None):
        attachment_id = attachment_id or blog.plan_attachment(slug, name)
        return blog.save_attachment(slug, attachment_id, name, "text/plain", size, "ab" * 32, text)

    @pytest.mark.unit
    def test_attach_and_list(self, blog, post):
        record = self.attach(blog, post, "b.py")
        self.attach(blog, post, "A.txt")
        assert record["replaced"] is False and len(record["id"]) == 32
        assert [a["filename"] for a in blog.list_attachments(post)] == ["A.txt", "b.py"]  # by name, ignoring case

    @pytest.mark.unit
    def test_a_record_describes_the_file(self, blog, post):
        record = self.attach(blog, post, "data.csv", size=1234, text=False)
        assert (record["filename"], record["size"], record["is_text"], record["content_type"]) == ("data.csv", 1234, False, "text/plain")
        assert set(record) == {"id", "filename", "content_type", "size", "sha256", "is_text", "created_at", "replaced"}

    @pytest.mark.unit
    def test_the_same_name_replaces_the_file_and_keeps_its_id_so_links_keep_working(self, blog, post):
        first = self.attach(blog, post, "notes.md", size=5)
        second = self.attach(blog, post, "notes.md", size=99)
        assert second["id"] == first["id"] and second["replaced"] is True and second["size"] == 99
        assert len(blog.list_attachments(post)) == 1

    @pytest.mark.unit
    def test_the_same_name_on_different_posts_is_two_files(self, blog, post):
        blog.create_post("Other", "x")
        assert self.attach(blog, post, "a.txt")["id"] != self.attach(blog, "other", "a.txt")["id"]

    @pytest.mark.unit
    def test_names_are_case_sensitive(self, blog, post):
        assert self.attach(blog, post, "a.txt")["id"] != self.attach(blog, post, "A.txt")["id"]

    @pytest.mark.unit
    def test_a_post_can_hold_a_limited_number_of_files(self, blog, post):
        for i in range(MAX_ATTACHMENTS_PER_POST):
            self.attach(blog, post, f"f{i}.txt")
        with pytest.raises(BlogError, match="at most 50 attachments"):
            blog.plan_attachment(post, "one-too-many.txt")
        with pytest.raises(BlogError, match="at most 50"):
            blog.save_attachment(post, "0" * 32, "one-too-many.txt", "text/plain", 1, "ab" * 32, True)
        assert blog.plan_attachment(post, "f0.txt")  # replacing an existing one is still fine at the limit

    @pytest.mark.unit
    def test_an_unknown_post_is_not_found(self, blog):
        with pytest.raises(NotFound):
            blog.plan_attachment("ghost", "a.txt")
        with pytest.raises(NotFound):
            blog.list_attachments("ghost")

    @pytest.mark.unit
    def test_get_includes_the_post_it_belongs_to(self, blog, post):
        record = self.attach(blog, post, "a.txt")
        found = blog.get_attachment(record["id"])
        assert (found["post_slug"], found["post_status"]) == (post, "published")
        blog.set_status(post, "draft")
        assert blog.get_attachment(record["id"])["post_status"] == "draft"

    @pytest.mark.unit
    @pytest.mark.parametrize("missing", ["0" * 32, "", "../x", "x' OR '1'='1"])
    def test_get_missing(self, blog, missing):
        with pytest.raises(NotFound):
            blog.get_attachment(missing)

    @pytest.mark.unit
    def test_delete_only_removes_from_the_post_named(self, blog, post):
        blog.create_post("Other", "x")
        record = self.attach(blog, post, "a.txt")
        assert blog.delete_attachment("other", record["id"]) is False  # wrong post
        assert blog.delete_attachment(post, record["id"]) is True
        assert blog.delete_attachment(post, record["id"]) is False
        assert blog.list_attachments(post) == []

    @pytest.mark.unit
    def test_deleting_a_post_removes_its_attachment_records(self, blog, post):
        record = self.attach(blog, post, "a.txt")
        blog.delete_post(post)
        with pytest.raises(NotFound):
            blog.get_attachment(record["id"])

    @pytest.mark.unit
    def test_posts_report_how_many_files_are_attached(self, blog, post):
        self.attach(blog, post, "a.txt")
        self.attach(blog, post, "b.txt")
        blog.create_post("Bare", "x")
        assert blog.get_post(post)["attachment_count"] == 2 and len(blog.get_post(post)["attachments"]) == 2
        counts = {p["slug"]: p["attachment_count"] for p in blog.list_posts()["posts"]}
        assert counts == {post: 2, "bare": 0}
        assert blog.search_posts("body")["posts"][0]["attachment_count"] == 2

    @pytest.mark.unit
    def test_attaching_does_not_count_as_editing_the_post(self, blog, post):
        before = blog.get_post(post)
        self.attach(blog, post, "a.txt")
        after = blog.get_post(post)
        # an editor open on the post must not be made stale by a file being attached
        assert (after["version"], after["updated_at"]) == (before["version"], before["updated_at"])

    @pytest.mark.unit
    def test_renaming_a_post_keeps_its_files(self, blog, post):
        self.attach(blog, post, "a.txt")
        blog.update_post(post, new_slug="renamed")
        assert [a["filename"] for a in blog.list_attachments("renamed")] == ["a.txt"]

    @pytest.mark.unit
    def test_filenames_with_sql_and_markup_are_stored_literally(self, blog, post):
        nasty = "x'); DROP TABLE posts;--<script>.txt"
        self.attach(blog, post, nasty)
        assert blog.list_attachments(post)[0]["filename"] == nasty and blog.stats()["total"] == 1

    @pytest.mark.unit
    def test_an_older_database_without_the_table_is_upgraded_in_place(self, tmp_path):
        import sqlite3

        store = BlogStore(tmp_path / "old")
        store.create_post("Kept", "body")
        conn = sqlite3.connect(store.db_path)
        conn.execute("DROP TABLE attachments")
        conn.commit()
        conn.close()
        reopened = BlogStore(tmp_path / "old")
        assert reopened.get_post("kept")["attachment_count"] == 0
