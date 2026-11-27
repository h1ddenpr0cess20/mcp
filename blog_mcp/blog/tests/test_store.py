"""Tests for BlogStore: post storage, validation, search, and tags."""

import os
import sqlite3
import stat

import pytest

from blog_app import BlogError, BlogStore, Conflict, NotFound
from blog_app.store import MAX_BODY_CHARS, MAX_TAGS, MAX_TITLE_CHARS, normalize_tag, slugify


class TestSlugAndTagHelpers:
    @pytest.mark.unit
    @pytest.mark.parametrize("text,expected", [
        ("Hello, World!", "hello-world"),
        ("  Spaces   everywhere  ", "spaces-everywhere"),
        ("Café Münch", "cafe-munch"),
        ("already-a-slug", "already-a-slug"),
        ("!!!", ""),
        ("日本語", ""),
    ])
    def test_slugify(self, text, expected):
        assert slugify(text) == expected

    @pytest.mark.unit
    def test_slugify_is_length_limited(self):
        assert len(slugify("word " * 100)) <= 100

    @pytest.mark.unit
    @pytest.mark.parametrize("raw,expected", [
        ("Python", "python"),
        ("#Notes", "notes"),
        ("  machine learning  ", "machine-learning"),
        ("", ""),
    ])
    def test_normalize_tag(self, raw, expected):
        assert normalize_tag(raw) == expected


class TestCreatePost:
    @pytest.mark.unit
    def test_defaults_to_draft(self, blog):
        post = blog.create_post("My First Post", "Hello there.")
        assert post["status"] == "draft"
        assert post["published_at"] is None
        assert post["slug"] == "my-first-post"
        assert post["title"] == "My First Post"
        assert post["body"] == "Hello there."
        assert post["created_at"] == post["updated_at"]

    @pytest.mark.unit
    def test_publish_on_create(self, blog):
        post = blog.create_post("Live", "Body", publish=True)
        assert post["status"] == "published"
        assert post["published_at"] == post["created_at"]

    @pytest.mark.unit
    def test_duplicate_titles_get_numbered_slugs(self, blog):
        slugs = [blog.create_post("Same Title")["slug"] for _ in range(3)]
        assert slugs == ["same-title", "same-title-2", "same-title-3"]

    @pytest.mark.unit
    def test_explicit_slug_is_normalized(self, blog):
        assert blog.create_post("T", slug="My Custom Slug!")["slug"] == "my-custom-slug"

    @pytest.mark.unit
    def test_explicit_duplicate_slug_is_an_error_not_renumbered(self, blog):
        blog.create_post("One", slug="taken")
        with pytest.raises(BlogError, match="already in use"):
            blog.create_post("Two", slug="taken")

    @pytest.mark.unit
    def test_unsluggable_title_still_gets_a_slug(self, blog):
        assert blog.create_post("日本語")["slug"] == "post"
        assert blog.create_post("🎉")["slug"] == "post-2"

    @pytest.mark.unit
    def test_unsluggable_explicit_slug_is_an_error(self, blog):
        with pytest.raises(BlogError, match="slug"):
            blog.create_post("Title", slug="???")

    @pytest.mark.unit
    def test_tags_are_normalized_deduplicated_and_sorted(self, blog):
        post = blog.create_post("T", tags=["Python", "#notes", "python", "Machine Learning", "  "])
        assert post["tags"] == ["machine-learning", "notes", "python"]

    @pytest.mark.unit
    def test_summary_defaults_to_excerpt_but_explicit_summary_wins(self, blog):
        derived = blog.create_post("A", "# Heading\n\nThe real opening.")
        assert derived["summary"] == "The real opening."
        explicit = blog.create_post("B", "Body text.", summary="Custom summary")
        assert explicit["summary"] == "Custom summary"

    @pytest.mark.unit
    def test_word_count(self, blog):
        assert blog.create_post("A", "# Heading\n\none two three")["word_count"] == 4

    @pytest.mark.unit
    def test_empty_body_is_allowed(self, blog):
        post = blog.create_post("Stub")
        assert post["body"] == ""
        assert post["word_count"] == 0

    @pytest.mark.unit
    @pytest.mark.parametrize("title", ["", "   ", None])
    def test_blank_title_is_rejected(self, blog, title):
        with pytest.raises(BlogError, match="title"):
            blog.create_post(title)

    @pytest.mark.unit
    def test_overlong_title_is_rejected(self, blog):
        with pytest.raises(BlogError, match="title"):
            blog.create_post("x" * (MAX_TITLE_CHARS + 1))

    @pytest.mark.unit
    def test_overlong_body_is_rejected(self, blog):
        with pytest.raises(BlogError, match="body"):
            blog.create_post("T", "x" * (MAX_BODY_CHARS + 1))

    @pytest.mark.unit
    def test_too_many_tags_are_rejected(self, blog):
        with pytest.raises(BlogError, match="tags"):
            blog.create_post("T", tags=[f"tag{i}" for i in range(MAX_TAGS + 1)])

    @pytest.mark.unit
    def test_tags_as_a_bare_string_are_rejected(self, blog):
        with pytest.raises(BlogError, match="list"):
            blog.create_post("T", tags="python")

    @pytest.mark.unit
    def test_failed_create_leaves_nothing_behind(self, blog):
        with pytest.raises(BlogError):
            blog.create_post("T", tags=[f"tag{i}" for i in range(MAX_TAGS + 1)])
        assert blog.stats()["total"] == 0

    @pytest.mark.unit
    def test_sql_metacharacters_are_stored_literally(self, blog):
        post = blog.create_post("Robert'); DROP TABLE posts;--", "x' OR '1'='1")
        assert blog.get_post(post["slug"])["title"] == "Robert'); DROP TABLE posts;--"
        assert blog.stats()["total"] == 1


class TestGetAndList:
    @pytest.mark.unit
    def test_get_missing_post(self, blog):
        with pytest.raises(BlogError, match="not found"):
            blog.get_post("nope")

    @pytest.mark.unit
    def test_get_returns_body_but_list_does_not(self, blog):
        blog.create_post("A", "the body")
        assert blog.get_post("a")["body"] == "the body"
        assert "body" not in blog.list_posts()["posts"][0]

    @pytest.mark.unit
    def test_published_posts_sort_by_publish_date_newest_first(self, blog, clock):
        for title in ("first", "second", "third"):
            blog.create_post(title, publish=True)
            clock()
        assert [p["slug"] for p in blog.list_posts()["posts"]] == ["third", "second", "first"]

    @pytest.mark.unit
    def test_status_filter(self, blog):
        blog.create_post("draft one")
        blog.create_post("live one", publish=True)
        assert [p["slug"] for p in blog.list_posts(status="draft")["posts"]] == ["draft-one"]
        assert [p["slug"] for p in blog.list_posts(status="published")["posts"]] == ["live-one"]
        assert blog.list_posts(status="all")["total"] == 2

    @pytest.mark.unit
    def test_invalid_status_is_rejected(self, blog):
        with pytest.raises(BlogError, match="status"):
            blog.list_posts(status="archived")

    @pytest.mark.unit
    def test_tag_filter_is_case_insensitive(self, blog):
        blog.create_post("a", tags=["Python"])
        blog.create_post("b", tags=["rust"])
        assert [p["slug"] for p in blog.list_posts(tag="PYTHON")["posts"]] == ["a"]
        assert [p["slug"] for p in blog.list_posts(tag="#rust")["posts"]] == ["b"]
        assert blog.list_posts(tag="go")["posts"] == []

    @pytest.mark.unit
    def test_pagination(self, blog, clock):
        for i in range(5):
            blog.create_post(f"post {i}", publish=True)
            clock()
        page1 = blog.list_posts(limit=2, offset=0)
        page3 = blog.list_posts(limit=2, offset=4)
        assert page1["total"] == 5
        assert [p["slug"] for p in page1["posts"]] == ["post-4", "post-3"]
        assert [p["slug"] for p in page3["posts"]] == ["post-0"]

    @pytest.mark.unit
    def test_limit_and_offset_are_clamped(self, blog):
        blog.create_post("a")
        result = blog.list_posts(limit=10_000, offset=-5)
        assert result["limit"] == 100
        assert result["offset"] == 0
        assert blog.list_posts(limit=0)["limit"] == 1

    @pytest.mark.unit
    @pytest.mark.parametrize("offset", [10**30, 2**63, -(10**30)])
    def test_absurd_offsets_do_not_overflow_sqlite(self, blog, offset):
        blog.create_post("a")
        result = blog.list_posts(offset=offset)
        assert result["total"] == 1
        assert result["offset"] in (0, 10**9)

    @pytest.mark.unit
    def test_list_includes_tags(self, blog):
        blog.create_post("a", tags=["x", "y"])
        assert blog.list_posts()["posts"][0]["tags"] == ["x", "y"]


class TestUpdatePost:
    @pytest.mark.unit
    def test_update_title_and_body_recomputes_derived_fields(self, blog, clock):
        blog.create_post("Old", "one two")
        clock()
        post = blog.update_post("old", title="New", body="a b c d e")
        assert post["title"] == "New"
        assert post["body"] == "a b c d e"
        assert post["word_count"] == 5
        assert post["summary"] == "a b c d e"
        assert post["updated_at"] > post["created_at"]
        assert post["slug"] == "old"  # slug is stable unless new_slug is given

    @pytest.mark.unit
    def test_empty_fields_are_left_alone(self, blog):
        blog.create_post("Title", "Body", tags=["keep"], summary="Sum")
        post = blog.update_post("title", title="Renamed")
        assert (post["body"], post["tags"], post["summary"]) == ("Body", ["keep"], "Sum")

    @pytest.mark.unit
    def test_tags_replace_or_clear(self, blog):
        blog.create_post("T", tags=["a", "b"])
        assert blog.update_post("t", tags=["c"])["tags"] == ["c"]
        assert blog.update_post("t", tags=[])["tags"] == []

    @pytest.mark.unit
    def test_tags_none_means_unchanged(self, blog):
        blog.create_post("T", tags=["a"])
        assert blog.update_post("t", title="T2")["tags"] == ["a"]

    @pytest.mark.unit
    def test_rename_slug(self, blog):
        blog.create_post("T", "body")
        post = blog.update_post("t", new_slug="Better Slug")
        assert post["slug"] == "better-slug"
        assert blog.get_post("better-slug")["body"] == "body"
        with pytest.raises(BlogError):
            blog.get_post("t")

    @pytest.mark.unit
    def test_rename_slug_collision(self, blog):
        blog.create_post("A")
        blog.create_post("B")
        with pytest.raises(BlogError, match="already in use"):
            blog.update_post("a", new_slug="b")

    @pytest.mark.unit
    def test_renaming_slug_to_itself_is_fine(self, blog):
        blog.create_post("A")
        assert blog.update_post("a", new_slug="a")["slug"] == "a"

    @pytest.mark.unit
    def test_nothing_to_update(self, blog):
        blog.create_post("A")
        with pytest.raises(BlogError, match="Nothing to update"):
            blog.update_post("a")

    @pytest.mark.unit
    def test_update_missing_post(self, blog):
        with pytest.raises(BlogError, match="not found"):
            blog.update_post("ghost", title="x")

    @pytest.mark.unit
    def test_failed_update_changes_nothing(self, blog):
        blog.create_post("A", "body", tags=["keep"])
        blog.create_post("B")
        with pytest.raises(BlogError):
            blog.update_post("a", title="Changed", new_slug="b")
        post = blog.get_post("a")
        assert (post["title"], post["tags"]) == ("A", ["keep"])


class TestReplaceInPost:
    @pytest.mark.unit
    def test_single_replacement(self, blog):
        blog.create_post("T", "The quick brown fox.")
        post = blog.replace_in_post("t", "quick", "slow")
        assert post["body"] == "The slow brown fox."
        assert post["replacements"] == 1

    @pytest.mark.unit
    def test_ambiguous_match_is_an_error(self, blog):
        blog.create_post("T", "cat and cat")
        with pytest.raises(BlogError, match="2 times"):
            blog.replace_in_post("t", "cat", "dog")
        assert blog.get_post("t")["body"] == "cat and cat"

    @pytest.mark.unit
    def test_replace_all(self, blog):
        blog.create_post("T", "cat and cat")
        post = blog.replace_in_post("t", "cat", "dog", replace_all=True)
        assert post["body"] == "dog and dog"
        assert post["replacements"] == 2

    @pytest.mark.unit
    def test_not_found(self, blog):
        blog.create_post("T", "hello")
        with pytest.raises(BlogError, match="not found"):
            blog.replace_in_post("t", "absent", "x")

    @pytest.mark.unit
    def test_empty_find_is_rejected(self, blog):
        blog.create_post("T", "hello")
        with pytest.raises(BlogError, match="find"):
            blog.replace_in_post("t", "", "x")

    @pytest.mark.unit
    def test_empty_replacement_deletes_text(self, blog):
        blog.create_post("T", "keep this removeme end")
        assert blog.replace_in_post("t", " removeme", "")["body"] == "keep this end"

    @pytest.mark.unit
    def test_derived_fields_follow_the_edit(self, blog):
        blog.create_post("T", "one two")
        assert blog.replace_in_post("t", "two", "two three four")["word_count"] == 4

    @pytest.mark.unit
    def test_replacement_cannot_exceed_body_limit(self, blog):
        blog.create_post("T", "x")
        with pytest.raises(BlogError, match="body"):
            blog.replace_in_post("t", "x", "y" * (MAX_BODY_CHARS + 1))
        assert blog.get_post("t")["body"] == "x"


class TestStatus:
    @pytest.mark.unit
    def test_publish_and_unpublish(self, blog):
        blog.create_post("T")
        published = blog.set_status("t", "published")
        assert published["status"] == "published"
        assert published["published_at"]
        assert blog.set_status("t", "draft")["status"] == "draft"

    @pytest.mark.unit
    def test_republishing_keeps_the_original_publication_date(self, blog, clock):
        blog.create_post("T", publish=True)
        first = blog.get_post("t")["published_at"]
        clock(60)
        blog.set_status("t", "draft")
        clock(60)
        assert blog.set_status("t", "published")["published_at"] == first

    @pytest.mark.unit
    def test_publishing_twice_is_harmless(self, blog, clock):
        blog.create_post("T", publish=True)
        first = blog.get_post("t")["published_at"]
        clock()
        assert blog.set_status("t", "published")["published_at"] == first

    @pytest.mark.unit
    def test_invalid_status(self, blog):
        blog.create_post("T")
        with pytest.raises(BlogError, match="status"):
            blog.set_status("t", "archived")

    @pytest.mark.unit
    def test_missing_post(self, blog):
        with pytest.raises(BlogError, match="not found"):
            blog.set_status("ghost", "published")


class TestDelete:
    @pytest.mark.unit
    def test_delete(self, blog):
        blog.create_post("T", tags=["x"])
        assert blog.delete_post("t") is True
        assert blog.delete_post("t") is False
        with pytest.raises(BlogError):
            blog.get_post("t")

    @pytest.mark.unit
    def test_delete_removes_tag_rows(self, blog):
        blog.create_post("T", tags=["x"])
        blog.delete_post("t")
        assert blog.list_tags()["tags"] == []

    @pytest.mark.unit
    def test_slug_can_be_reused_after_delete(self, blog):
        blog.create_post("T")
        blog.delete_post("t")
        assert blog.create_post("T")["slug"] == "t"


class TestSearch:
    @pytest.fixture(autouse=True)
    def _posts(self, blog):
        blog.create_post("Gardening notes", "Tomatoes need full sun and regular water.", tags=["garden"], publish=True)
        blog.create_post("Rust ownership", "Borrowing rules keep memory safe.", tags=["rust", "programming"], publish=True)
        blog.create_post("Draft idea", "Write about tomato blight someday.")
        blog.create_post("École", "Les élèves de l'ÉCOLE.", publish=True)

    @pytest.mark.unit
    def test_matches_body(self, blog):
        assert [p["slug"] for p in blog.search_posts("tomatoes")["posts"]] == ["gardening-notes"]

    @pytest.mark.unit
    def test_matches_title_and_tags(self, blog):
        assert [p["slug"] for p in blog.search_posts("ownership")["posts"]] == ["rust-ownership"]
        assert [p["slug"] for p in blog.search_posts("programming")["posts"]] == ["rust-ownership"]

    @pytest.mark.unit
    def test_case_insensitive_including_non_ascii(self, blog):
        assert [p["slug"] for p in blog.search_posts("TOMATOES")["posts"]] == ["gardening-notes"]
        assert [p["slug"] for p in blog.search_posts("école")["posts"]] == ["ecole"]
        assert [p["slug"] for p in blog.search_posts("ÉCOLE")["posts"]] == ["ecole"]

    @pytest.mark.unit
    def test_every_word_must_match(self, blog):
        assert [p["slug"] for p in blog.search_posts("memory borrowing")["posts"]] == ["rust-ownership"]
        assert blog.search_posts("memory tomatoes")["posts"] == []

    @pytest.mark.unit
    def test_status_filter(self, blog):
        assert blog.search_posts("tomato")["count"] == 2
        assert [p["slug"] for p in blog.search_posts("tomato", status="draft")["posts"]] == ["draft-idea"]
        assert [p["slug"] for p in blog.search_posts("tomato", status="published")["posts"]] == ["gardening-notes"]

    @pytest.mark.unit
    def test_wildcards_are_literal(self, blog):
        assert blog.search_posts("%")["posts"] == []
        assert blog.search_posts("_")["posts"] == []

    @pytest.mark.unit
    def test_snippet_shows_matching_text(self, blog):
        result = blog.search_posts("borrowing")["posts"][0]
        assert "Borrowing rules" in result["snippet"]

    @pytest.mark.unit
    def test_snippet_is_windowed_for_long_posts(self, blog):
        blog.create_post("Long", ("filler " * 200) + "needle " + ("filler " * 200))
        snippet = blog.search_posts("needle")["posts"][0]["snippet"]
        assert "needle" in snippet
        assert snippet.startswith("…")
        assert snippet.endswith("…")
        assert len(snippet) < 300

    @pytest.mark.unit
    def test_empty_query_is_rejected(self, blog):
        for query in ("", "   ", None):
            with pytest.raises(BlogError, match="query"):
                blog.search_posts(query)

    @pytest.mark.unit
    def test_no_match(self, blog):
        assert blog.search_posts("zzzzzz") == {"query": "zzzzzz", "posts": [], "count": 0}

    @pytest.mark.unit
    def test_sql_injection_attempt_is_inert(self, blog):
        assert blog.search_posts("' OR 1=1 --")["posts"] == []
        assert blog.stats()["total"] == 4


class TestTagsAndStats:
    @pytest.mark.unit
    def test_tag_counts_most_used_first(self, blog):
        blog.create_post("a", tags=["x", "y"])
        blog.create_post("b", tags=["x"])
        assert blog.list_tags() == {"tags": [{"tag": "x", "count": 2}, {"tag": "y", "count": 1}], "count": 2}

    @pytest.mark.unit
    def test_tag_counts_respect_status(self, blog):
        blog.create_post("a", tags=["x"], publish=True)
        blog.create_post("b", tags=["x", "only-draft"])
        assert blog.list_tags(status="published")["tags"] == [{"tag": "x", "count": 1}]
        assert blog.list_tags(status="draft")["count"] == 2

    @pytest.mark.unit
    def test_stats(self, blog):
        assert blog.stats() == {"total": 0, "published": 0, "drafts": 0, "tags": 0}
        blog.create_post("a", tags=["x"], publish=True)
        blog.create_post("b", tags=["x", "y"])
        assert blog.stats() == {"total": 2, "published": 1, "drafts": 1, "tags": 2}


class TestStorage:
    @pytest.mark.unit
    def test_posts_persist_across_instances(self, blog):
        blog.create_post("Persistent", "still here", tags=["t"], publish=True)
        reopened = BlogStore(data_dir=str(blog.data_dir))
        post = reopened.get_post("persistent")
        assert (post["body"], post["tags"], post["status"]) == ("still here", ["t"], "published")

    @pytest.mark.unit
    def test_data_dir_defaults_to_blog_dir_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BLOG_DIR", str(tmp_path / "from-env"))
        assert BlogStore().data_dir == tmp_path / "from-env"

    @pytest.mark.unit
    def test_unicode_round_trip(self, blog):
        blog.create_post("Ünïcödé 🎉", "日本語のテキスト")
        assert blog.get_post("unicode")["body"] == "日本語のテキスト"

    @pytest.mark.unit
    @pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
    def test_new_data_dir_and_database_are_owner_only(self, blog):
        assert stat.S_IMODE(os.stat(blog.data_dir).st_mode) == 0o700
        assert stat.S_IMODE(os.stat(blog.db_path).st_mode) == 0o600

    @pytest.mark.unit
    @pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
    def test_existing_directory_permissions_are_not_changed(self, tmp_path):
        shared = tmp_path / "shared"
        shared.mkdir()
        unusual = stat.S_IRWXU | stat.S_IXGRP  # differs from the 0o700 a new data folder gets
        os.chmod(shared, unusual)
        BlogStore(data_dir=str(shared))
        assert stat.S_IMODE(os.stat(shared).st_mode) == unusual


class TestVersioningAndConflicts:
    @pytest.mark.unit
    def test_new_posts_start_at_version_one(self, blog):
        assert blog.create_post("T")["version"] == 1

    @pytest.mark.unit
    def test_every_change_bumps_the_version(self, blog):
        blog.create_post("T", "body")
        assert blog.update_post("t", title="T2")["version"] == 2
        assert blog.replace_in_post("t", "body", "text")["version"] == 3
        assert blog.set_status("t", "published")["version"] == 4

    @pytest.mark.unit
    def test_matching_expected_version_is_accepted(self, blog):
        post = blog.create_post("T")
        assert blog.update_post("t", title="New", expected_version=post["version"])["title"] == "New"

    @pytest.mark.unit
    def test_stale_expected_version_is_a_conflict_and_changes_nothing(self, blog):
        post = blog.create_post("T", "mine")
        blog.update_post("t", body="theirs")  # someone else edits first
        with pytest.raises(Conflict, match="changed by someone else"):
            blog.update_post("t", body="stale overwrite", expected_version=post["version"])
        assert blog.get_post("t")["body"] == "theirs"

    @pytest.mark.unit
    def test_without_expected_version_the_last_writer_wins(self, blog):
        blog.create_post("T")
        blog.update_post("t", body="first")
        assert blog.update_post("t", body="second")["body"] == "second"

    @pytest.mark.unit
    def test_write_racing_another_write_is_a_conflict_not_a_lost_update(self, blog, monkeypatch):
        blog.create_post("T", "start")
        original = BlogStore._require

        def require_then_get_overtaken(conn, slug):
            row = original(conn, slug)
            # Another writer commits between our read and our write.
            other = sqlite3.connect(blog.db_path)
            other.execute("UPDATE posts SET version = version + 1, body = 'other writer' WHERE slug = ?", (slug,))
            other.commit()
            other.close()
            return row

        with monkeypatch.context() as patched:
            patched.setattr(BlogStore, "_require", staticmethod(require_then_get_overtaken))
            with pytest.raises(Conflict, match="same moment"):
                blog.update_post("t", body="mine")
        assert blog.get_post("t")["body"] == "other writer"

    @pytest.mark.unit
    def test_error_types(self, blog):
        blog.create_post("A")
        with pytest.raises(NotFound):
            blog.get_post("ghost")
        with pytest.raises(Conflict):
            blog.create_post("B", slug="a")
        with pytest.raises(BlogError) as bad_input:
            blog.create_post("")
        assert not isinstance(bad_input.value, (NotFound, Conflict))


class TestClearingFields:
    @pytest.mark.unit
    def test_empty_string_clears_a_summary(self, blog):
        blog.create_post("T", "Opening line.", summary="Custom")
        post = blog.update_post("t", summary="")
        assert post["custom_summary"] == ""
        assert post["summary"] == "Opening line."

    @pytest.mark.unit
    def test_empty_string_clears_a_body(self, blog):
        blog.create_post("T", "something")
        post = blog.update_post("t", body="")
        assert (post["body"], post["word_count"]) == ("", 0)

    @pytest.mark.unit
    def test_empty_title_is_still_rejected(self, blog):
        blog.create_post("T")
        with pytest.raises(BlogError, match="title"):
            blog.update_post("t", title="")

    @pytest.mark.unit
    def test_custom_summary_is_separate_from_the_derived_one(self, blog):
        derived = blog.create_post("A", "Opening paragraph.")
        assert (derived["summary"], derived["custom_summary"]) == ("Opening paragraph.", "")
        custom = blog.create_post("B", "Opening paragraph.", summary="Mine")
        assert (custom["summary"], custom["custom_summary"]) == ("Mine", "Mine")


class TestNewlines:
    @pytest.mark.unit
    def test_browser_style_crlf_is_stored_as_lf(self, blog):
        post = blog.create_post("T", "line one\r\nline two\rline three")
        assert post["body"] == "line one\nline two\nline three"

    @pytest.mark.unit
    def test_update_normalizes_too(self, blog):
        blog.create_post("T")
        assert blog.update_post("t", body="a\r\nb")["body"] == "a\nb"

    @pytest.mark.unit
    def test_replace_matches_across_crlf_differences(self, blog):
        blog.create_post("T", "first line\nsecond line")
        post = blog.replace_in_post("t", "first line\r\nsecond line", "joined")
        assert post["body"] == "joined"


class TestDerivedFields:
    @staticmethod
    def corrupt(store, user_version):
        conn = sqlite3.connect(store.db_path)
        conn.execute("UPDATE posts SET excerpt = 'stale excerpt', word_count = 999")
        conn.execute(f"PRAGMA user_version = {user_version}")
        conn.commit()
        conn.close()

    @pytest.mark.unit
    def test_outdated_excerpts_and_word_counts_are_rebuilt_on_startup(self, blog):
        blog.create_post("T", "Real opening paragraph.\n\n- a list item", publish=True)
        before = blog.get_post("t")
        self.corrupt(blog, user_version=0)
        reopened = BlogStore(blog.data_dir)
        after = reopened.get_post("t")
        assert after["summary"] == "Real opening paragraph."
        assert after["word_count"] == before["word_count"]

    @pytest.mark.unit
    def test_rebuilding_does_not_count_as_an_edit(self, blog):
        blog.create_post("T", "body", publish=True)
        before = blog.get_post("t")
        self.corrupt(blog, user_version=0)
        after = BlogStore(blog.data_dir).get_post("t")
        keys = ("version", "updated_at", "published_at")
        assert [after[k] for k in keys] == [before[k] for k in keys]

    @pytest.mark.unit
    def test_up_to_date_data_is_left_alone(self, blog):
        from blog_app.store import DERIVED_VERSION

        blog.create_post("T", "body")
        self.corrupt(blog, user_version=DERIVED_VERSION)
        assert BlogStore(blog.data_dir).get_post("t")["summary"] == "stale excerpt"  # not touched: the version matched

    @pytest.mark.unit
    def test_a_new_blog_is_marked_current(self, blog):
        from blog_app.store import DERIVED_VERSION

        conn = sqlite3.connect(blog.db_path)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == DERIVED_VERSION
        conn.close()
