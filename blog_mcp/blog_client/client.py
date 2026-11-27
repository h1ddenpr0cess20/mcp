import os
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastmcp.exceptions import ToolError

from .render import make_excerpt, plain_text, word_count

MAX_TITLE_CHARS = 200
MAX_SUMMARY_CHARS = 500
MAX_BODY_CHARS = 1_000_000
MAX_TAGS = 20
MAX_TAG_CHARS = 50
MAX_SLUG_CHARS = 100
MAX_SEARCH_TERMS = 8
MAX_OFFSET = 10**9  # far beyond any real blog; keeps OFFSET inside SQLite's integer range

STATUSES = ("draft", "published")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    slug         TEXT NOT NULL UNIQUE,
    title        TEXT NOT NULL,
    body         TEXT NOT NULL DEFAULT '',
    summary      TEXT NOT NULL DEFAULT '',
    excerpt      TEXT NOT NULL DEFAULT '',
    word_count   INTEGER NOT NULL DEFAULT 0,
    status       TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')),
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    published_at TEXT
);
CREATE TABLE IF NOT EXISTS post_tags (
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    tag     TEXT NOT NULL,
    PRIMARY KEY (post_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_post_tags_tag ON post_tags(tag);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
"""

# Published posts sort by publish date; drafts by when they were last edited.
_ORDER = "CASE WHEN p.status = 'published' THEN p.published_at ELSE p.updated_at END DESC, p.id DESC"


class BlogError(ToolError):
    """Raised for invalid input or a missing post.

    A ToolError so FastMCP reports it to the model as a normal tool failure, with its
    message intact, and logs one line instead of a traceback for an expected problem.
    """


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(text: str) -> str:
    """Turn arbitrary text into a lowercase, hyphen-separated URL slug (possibly empty)."""
    ascii_text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:MAX_SLUG_CHARS].strip("-")


def normalize_tag(tag: str) -> str:
    """Lowercase a tag, drop a leading '#', and join words with hyphens."""
    return re.sub(r"\s+", "-", str(tag).strip().lstrip("#").strip().lower())


def _normalize_tags(tags) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        raise BlogError("tags must be a list of strings")
    result = []
    for tag in tags:
        clean = normalize_tag(tag)
        if not clean:
            continue
        if len(clean) > MAX_TAG_CHARS:
            raise BlogError(f"Tag '{clean[:20]}...' is longer than {MAX_TAG_CHARS} characters")
        if clean not in result:
            result.append(clean)
    if len(result) > MAX_TAGS:
        raise BlogError(f"A post can have at most {MAX_TAGS} tags")
    return sorted(result)


def _check_status(status: str) -> str:
    if status not in ("all",) + STATUSES:
        raise BlogError("status must be 'all', 'draft', or 'published'")
    return status


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def _casefold(value):
    return value.casefold() if isinstance(value, str) else ""


class BlogClient:
    """SQLite-backed store and business logic for the private blog."""

    def __init__(self, data_dir: str | None = None):
        self.data_dir = Path(os.path.expanduser(data_dir or os.getenv("BLOG_DIR", "~/mcp-blog")))
        created = not self.data_dir.exists()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if created:
            # Only tighten a directory we created; never chmod one the user pointed us at.
            os.chmod(self.data_dir, 0o700)
        self.db_path = self.data_dir / "blog.db"
        # Create the file ourselves so it is never briefly readable by other users.
        os.close(os.open(self.db_path, os.O_WRONLY | os.O_CREAT, 0o600))
        with self._db() as conn:
            conn.executescript(_SCHEMA)

    # --- internals ---------------------------------------------------------

    @contextmanager
    def _db(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.create_function("casefold", 1, _casefold, deterministic=True)
        try:
            with conn:  # commit on success, roll back on error
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _tags_for(conn, post_ids: list[int]) -> dict[int, list[str]]:
        tags: dict[int, list[str]] = {post_id: [] for post_id in post_ids}
        if post_ids:
            marks = ",".join("?" * len(post_ids))
            rows = conn.execute(f"SELECT post_id, tag FROM post_tags WHERE post_id IN ({marks}) ORDER BY tag", post_ids)
            for row in rows:
                tags[row["post_id"]].append(row["tag"])
        return tags

    @staticmethod
    def _to_dict(row, tags: list[str], with_body: bool = False) -> dict:
        post = {
            "slug": row["slug"],
            "title": row["title"],
            "status": row["status"],
            "tags": tags,
            "summary": row["summary"] or row["excerpt"],
            "word_count": row["word_count"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "published_at": row["published_at"],
        }
        if with_body:
            post["body"] = row["body"]
        return post

    @staticmethod
    def _require(conn, slug: str):
        row = conn.execute("SELECT * FROM posts WHERE slug = ?", (slug,)).fetchone()
        if row is None:
            raise BlogError(f"Post '{slug}' not found")
        return row

    def _full(self, conn, slug: str) -> dict:
        row = self._require(conn, slug)
        return self._to_dict(row, self._tags_for(conn, [row["id"]])[row["id"]], with_body=True)

    @staticmethod
    def _slug_taken(conn, slug: str, exclude_id: int | None = None) -> bool:
        row = conn.execute("SELECT id FROM posts WHERE slug = ?", (slug,)).fetchone()
        return row is not None and row["id"] != exclude_id

    def _unique_slug(self, conn, base: str) -> str:
        base = base or "post"
        candidate, n = base, 1
        while self._slug_taken(conn, candidate):
            n += 1
            suffix = f"-{n}"
            candidate = base[: MAX_SLUG_CHARS - len(suffix)].rstrip("-") + suffix
        return candidate

    @staticmethod
    def _set_tags(conn, post_id: int, tags: list[str]) -> None:
        conn.execute("DELETE FROM post_tags WHERE post_id = ?", (post_id,))
        conn.executemany("INSERT INTO post_tags (post_id, tag) VALUES (?, ?)", [(post_id, tag) for tag in tags])

    @staticmethod
    def _clean_title(title: str) -> str:
        title = (title or "").strip()
        if not title:
            raise BlogError("title must not be empty")
        if len(title) > MAX_TITLE_CHARS:
            raise BlogError(f"title is longer than {MAX_TITLE_CHARS} characters")
        return title

    @staticmethod
    def _clean_body(body: str) -> str:
        body = body or ""
        if len(body) > MAX_BODY_CHARS:
            raise BlogError(f"body is longer than {MAX_BODY_CHARS} characters")
        return body

    @staticmethod
    def _clean_summary(summary: str) -> str:
        summary = (summary or "").strip()
        if len(summary) > MAX_SUMMARY_CHARS:
            raise BlogError(f"summary is longer than {MAX_SUMMARY_CHARS} characters")
        return summary

    @staticmethod
    def _clean_slug(slug: str) -> str:
        clean = slugify(slug)
        if not clean:
            raise BlogError("slug must contain at least one letter or digit")
        return clean

    # --- posts -------------------------------------------------------------

    def create_post(self, title: str, body: str = "", tags: list[str] | None = None, slug: str = "",
                    summary: str = "", publish: bool = False) -> dict:
        """Create a post. Returns the full post. Drafts are the default."""
        title = self._clean_title(title)
        body = self._clean_body(body)
        summary = self._clean_summary(summary)
        tag_list = _normalize_tags(tags)
        now = _now()
        with self._db() as conn:
            if slug:
                final_slug = self._clean_slug(slug)
                if self._slug_taken(conn, final_slug):
                    raise BlogError(f"Slug '{final_slug}' is already in use")
            else:
                final_slug = self._unique_slug(conn, slugify(title))
            cursor = conn.execute(
                "INSERT INTO posts (slug, title, body, summary, excerpt, word_count, status, created_at, updated_at, published_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (final_slug, title, body, summary, make_excerpt(body), word_count(body),
                 "published" if publish else "draft", now, now, now if publish else None),
            )
            self._set_tags(conn, cursor.lastrowid, tag_list)
            return self._full(conn, final_slug)

    def get_post(self, slug: str) -> dict:
        """Return a full post, including its Markdown body."""
        with self._db() as conn:
            return self._full(conn, slug)

    def list_posts(self, status: str = "all", tag: str = "", limit: int = 20, offset: int = 0) -> dict:
        """List posts without their bodies, newest first."""
        _check_status(status)
        limit, offset = _clamp(limit, 1, 100), _clamp(offset, 0, MAX_OFFSET)
        where, params = [], []
        if status != "all":
            where.append("p.status = ?")
            params.append(status)
        if tag:
            where.append("EXISTS (SELECT 1 FROM post_tags t WHERE t.post_id = p.id AND t.tag = ?)")
            params.append(normalize_tag(tag))
        clause = f" WHERE {' AND '.join(where)}" if where else ""
        with self._db() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM posts p{clause}", params).fetchone()[0]
            rows = conn.execute(f"SELECT p.* FROM posts p{clause} ORDER BY {_ORDER} LIMIT ? OFFSET ?",
                                params + [limit, offset]).fetchall()
            tags = self._tags_for(conn, [row["id"] for row in rows])
            posts = [self._to_dict(row, tags[row["id"]]) for row in rows]
        return {"posts": posts, "total": total, "limit": limit, "offset": offset}

    def update_post(self, slug: str, title: str = "", body: str = "", summary: str = "", tags: list[str] | None = None,
                    new_slug: str = "") -> dict:
        """Change any of a post's fields. Empty strings and tags=None leave a field as it is."""
        if not (title or body or summary or new_slug or tags is not None):
            raise BlogError("Nothing to update: pass at least one field to change")
        title = self._clean_title(title) if title else ""
        body = self._clean_body(body) if body else ""
        summary = self._clean_summary(summary) if summary else ""
        tag_list = _normalize_tags(tags) if tags is not None else None
        with self._db() as conn:
            row = self._require(conn, slug)
            fields = {"updated_at": _now()}
            if title:
                fields["title"] = title
            if body:
                fields.update(body=body, excerpt=make_excerpt(body), word_count=word_count(body))
            if summary:
                fields["summary"] = summary
            if new_slug:
                clean = self._clean_slug(new_slug)
                if self._slug_taken(conn, clean, exclude_id=row["id"]):
                    raise BlogError(f"Slug '{clean}' is already in use")
                fields["slug"] = clean
            self._apply(conn, row["id"], fields)
            if tag_list is not None:
                self._set_tags(conn, row["id"], tag_list)
            return self._full(conn, fields.get("slug", slug))

    def replace_in_post(self, slug: str, find: str, replace: str, replace_all: bool = False) -> dict:
        """Find and replace text in a post's body without resending the whole post."""
        if not find:
            raise BlogError("find must not be empty")
        with self._db() as conn:
            row = self._require(conn, slug)
            count = row["body"].count(find)
            if count == 0:
                raise BlogError("The text to replace was not found in the post body")
            if count > 1 and not replace_all:
                raise BlogError(f"The text appears {count} times; add surrounding context to make it unique or set replace_all")
            body = self._clean_body(row["body"].replace(find, replace) if replace_all else row["body"].replace(find, replace, 1))
            self._apply(conn, row["id"], {"body": body, "excerpt": make_excerpt(body),
                                          "word_count": word_count(body), "updated_at": _now()})
            post = self._full(conn, slug)
        post["replacements"] = count if replace_all else 1
        return post

    @staticmethod
    def _apply(conn, post_id: int, fields: dict) -> None:
        assignments = ", ".join(f"{name} = ?" for name in fields)
        conn.execute(f"UPDATE posts SET {assignments} WHERE id = ?", [*fields.values(), post_id])

    def set_status(self, slug: str, status: str) -> dict:
        """Publish a post or return it to draft. published_at records the first publication."""
        if status not in STATUSES:
            raise BlogError("status must be 'draft' or 'published'")
        with self._db() as conn:
            row = self._require(conn, slug)
            fields = {"status": status, "updated_at": _now()}
            if status == "published" and not row["published_at"]:
                fields["published_at"] = fields["updated_at"]
            self._apply(conn, row["id"], fields)
            return self._full(conn, slug)

    def delete_post(self, slug: str) -> bool:
        """Permanently delete a post. Returns False if it did not exist."""
        with self._db() as conn:
            return conn.execute("DELETE FROM posts WHERE slug = ?", (slug,)).rowcount > 0

    # --- discovery ---------------------------------------------------------

    def search_posts(self, query: str, status: str = "all", limit: int = 20) -> dict:
        """Case-insensitive search of titles, summaries, bodies, and tags. Every word must match."""
        _check_status(status)
        terms = [term.casefold() for term in (query or "").split()][:MAX_SEARCH_TERMS]
        if not terms:
            raise BlogError("query must not be empty")
        limit = _clamp(limit, 1, 50)
        where, params = [], []
        if status != "all":
            where.append("p.status = ?")
            params.append(status)
        for term in terms:
            where.append("(instr(casefold(p.title || char(10) || p.summary || char(10) || p.body), ?) > 0"
                         " OR EXISTS (SELECT 1 FROM post_tags t WHERE t.post_id = p.id AND instr(t.tag, ?) > 0))")
            params += [term, term]
        with self._db() as conn:
            rows = conn.execute(f"SELECT p.* FROM posts p WHERE {' AND '.join(where)} ORDER BY {_ORDER} LIMIT ?",
                                params + [limit]).fetchall()
            tags = self._tags_for(conn, [row["id"] for row in rows])
            posts = []
            for row in rows:
                post = self._to_dict(row, tags[row["id"]])
                post["snippet"] = self._snippet(row, terms)
                posts.append(post)
        return {"query": query, "posts": posts, "count": len(posts)}

    @staticmethod
    def _snippet(row, terms: list[str], radius: int = 80) -> str:
        text = re.sub(r"\s+", " ", plain_text(row["body"])).strip()
        lowered = text.lower()
        hits = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
        if not hits:
            return row["summary"] or row["excerpt"]
        start = max(0, min(hits) - radius)
        end = min(len(text), min(hits) + radius * 2)
        return ("…" if start else "") + text[start:end].strip() + ("…" if end < len(text) else "")

    def list_tags(self, status: str = "all") -> dict:
        """List every tag with the number of posts using it, most used first."""
        _check_status(status)
        clause, params = ("", []) if status == "all" else (" WHERE p.status = ?", [status])
        with self._db() as conn:
            rows = conn.execute(
                "SELECT t.tag AS tag, COUNT(*) AS count FROM post_tags t JOIN posts p ON p.id = t.post_id"
                f"{clause} GROUP BY t.tag ORDER BY count DESC, t.tag", params).fetchall()
        tags = [{"tag": row["tag"], "count": row["count"]} for row in rows]
        return {"tags": tags, "count": len(tags)}

    def stats(self) -> dict:
        """Return post and tag counts."""
        with self._db() as conn:
            rows = conn.execute("SELECT status, COUNT(*) FROM posts GROUP BY status").fetchall()
            by_status = {row[0]: row[1] for row in rows}
            tag_count = conn.execute("SELECT COUNT(DISTINCT tag) FROM post_tags").fetchone()[0]
        return {
            "total": sum(by_status.values()),
            "published": by_status.get("published", 0),
            "drafts": by_status.get("draft", 0),
            "tags": tag_count,
        }
