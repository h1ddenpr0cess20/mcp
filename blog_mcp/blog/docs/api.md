# API Reference

The blog's JSON API, under `/api/v1`. It does everything the editor does, so scripts and the [`blog_mcp`](../../README.md) server can manage posts.

---

## Table of Contents

- [Authentication](#authentication)
- [Errors](#errors)
- [The Post Object](#the-post-object)
- [Endpoints](#endpoints)
- [Examples](#examples)

---

## Authentication

Every request needs the API token as a bearer token:

```
Authorization: Bearer <token>
```

The token is `BLOG_API_TOKEN` if you set it, otherwise the one the blog generated into `$BLOG_DIR/api_token`. A browser login does not work as an API credential, and the token does not open the website or the editor; they are separate.

Send the token only over HTTPS unless the blog is on your own computer.

---

## Errors

Failures return JSON with a message: `{"error": "Post 'x' not found"}`.

| Status | Meaning |
|--------|---------|
| 400 | Invalid input (blank title, wrong type, bad parameter, text to replace not found) |
| 401 | Missing or wrong token |
| 404 | No such post, or no such endpoint |
| 405 | Wrong method for the endpoint |
| 409 | Conflict: a slug already in use, or the post was changed since you loaded it |
| 413 | Request body too large |
| 500 | Unexpected error (details are in the blog's own log, not the response) |

---

## The Post Object

| Field          | Type        | Description |
|----------------|-------------|-------------|
| slug           | string      | The post's identifier and address |
| title          | string      | Post title |
| status         | string      | `"draft"` or `"published"` |
| tags           | list        | Tags, alphabetical |
| summary        | string      | The author's summary, or an excerpt of the opening paragraphs |
| word_count     | integer     | Words in the body, not counting Markdown syntax |
| version        | integer     | Starts at 1 and rises with every change |
| created_at     | string      | UTC timestamp, e.g. `2026-11-27T14:30:00Z` |
| updated_at     | string      | UTC timestamp of the last change |
| published_at   | string/null | When it was first published; `null` if never |
| url            | string      | The post's address on the blog (uses `BLOG_PUBLIC_URL` if set) |
| body           | string      | Markdown source (full posts only, not in lists) |
| custom_summary | string      | Only what the author wrote as a summary (full posts only) |

Lists and search results omit `body` and `custom_summary`; search results add `snippet`.

---

## Endpoints

### `GET /api/v1/info`
The blog's `title`, `description`, `public` (whether visitors can read published posts), `url`, and `posts` counts (`total`, `published`, `drafts`, `tags`).

### `GET /api/v1/posts`
List posts, newest first. Query: `status` (`all`, `draft`, `published`), `tag`, `limit` (1–100, default 20), `offset`. Returns `posts`, `total`, `limit`, `offset`.

### `POST /api/v1/posts`
Create a post. JSON body: `title` (required), `body`, `tags` (list), `slug`, `summary`, `publish` (boolean). Returns `201` with the post. Without `slug`, one is made from the title and numbered if taken; an explicit `slug` that is taken is a `409`.

### `GET /api/v1/posts/{slug}`
One full post.

### `PATCH /api/v1/posts/{slug}`
Change a post. JSON body with any of `title`, `body`, `summary`, `tags`, `slug` (the new slug). A field that is absent or `null` is left alone; `""` clears a summary or body, and `[]` clears the tags. At least one field is required. Optionally include `expected_version`: if the post has changed since that version, the request is a `409` and nothing is changed.

### `POST /api/v1/posts/{slug}/replace`
Find and replace in the body. JSON body: `find` (required), `replace`, `replace_all` (boolean). Fails with `400` if `find` is not present, or appears more than once while `replace_all` is false. Returns the post and `replacements`.

### `POST /api/v1/posts/{slug}/publish` and `/unpublish`
Publish a post, or return it to draft. `published_at` records the first publication and is kept if you republish.

### `DELETE /api/v1/posts/{slug}`
Delete permanently. Returns `{"slug": ..., "deleted": true}`, or `404` if there is no such post.

### `GET /api/v1/search`
Query: `q` (required; every word must match, case-insensitive, in the title, summary, body, or tags), `status`, `limit` (1–50). Returns `query`, `posts` (each with a `snippet`), and `count`.

### `GET /api/v1/tags`
Query: `status`. Returns `tags` (each with `tag` and `count`, most used first) and `count`.

### `POST /api/v1/media`
Upload an image as multipart form data in a field named `file`. PNG, JPEG, GIF, and WebP up to 8 MB, identified by content. Returns `201` with `url` (e.g. `/media/ab12….png`, for use in a post's Markdown) and `absolute_url`.

---

## Examples

```bash
TOKEN=$(cat ~/mcp-blog/api_token)
BLOG=http://127.0.0.1:9901

# Write and publish a post
curl -s -X POST $BLOG/api/v1/posts \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title": "Hello", "body": "First post.", "tags": ["notes"], "publish": true}'

# Fix a typo without resending the post
curl -s -X POST $BLOG/api/v1/posts/hello/replace \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"find": "First", "replace": "My first"}'

# Upload an image and use it
curl -s -X POST $BLOG/api/v1/media -H "Authorization: Bearer $TOKEN" -F file=@photo.png
```
