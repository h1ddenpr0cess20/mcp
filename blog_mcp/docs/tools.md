# Tool Reference

Complete reference for all tools exposed by the Blog MCP server.

Posts are identified by their **slug**, a short URL-safe name such as `my-first-post`. Every tool that returns a post includes its slug.

---

## Table of Contents

- [create\_post](#create_post)
- [get\_post](#get_post)
- [list\_posts](#list_posts)
- [update\_post](#update_post)
- [replace\_in\_post](#replace_in_post)
- [publish\_post](#publish_post)
- [unpublish\_post](#unpublish_post)
- [delete\_post](#delete_post)
- [search\_posts](#search_posts)
- [list\_tags](#list_tags)
- [get\_blog\_info](#get_blog_info)
- [The Post Object](#the-post-object)
- [Error Handling](#error-handling)

---

## create\_post

Create a post. It is saved as a draft unless `publish` is true.

**Parameters**

| Parameter | Type         | Required | Default | Description |
|-----------|--------------|----------|---------|-------------|
| title     | string       | yes      | —       | Post title (up to 200 characters). |
| body      | string       | no       | `""`    | Post content in Markdown. Raw HTML is shown as text, not rendered. |
| tags      | list[string] | no       | `[]`    | Tags for the post. Lowercased, `#` stripped, spaces become hyphens. |
| slug      | string       | no       | `""`    | URL slug. Empty derives one from the title and numbers it if taken. An explicit slug that is already used is an error. |
| summary   | string       | no       | `""`    | Short summary shown in lists. Empty uses the start of the body. |
| publish   | boolean      | no       | `false` | Publish immediately instead of saving a draft. |

**Returns**

A [post object](#the-post-object) including `body` and `url`.

**Use cases**

- Drafting a post for you to review before it goes live.
- Publishing a quick note in one call.

---

## get\_post

Get one post with its full Markdown body.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| slug      | string | yes      | The post's slug. |

**Returns**

A [post object](#the-post-object) including `body` and `url`.

---

## list\_posts

List posts without their bodies. Published posts are ordered by publish date, drafts by last edit, newest first.

**Parameters**

| Parameter | Type    | Required | Default | Description |
|-----------|---------|----------|---------|-------------|
| status    | string  | no       | `"all"` | `"all"`, `"draft"`, or `"published"`. |
| tag       | string  | no       | `""`    | Only posts with this tag. |
| limit     | integer | no       | `20`    | Posts to return, 1–100. |
| offset    | integer | no       | `0`     | Posts to skip, for paging. |

**Returns**

| Field  | Type    | Description |
|--------|---------|-------------|
| posts  | list    | [Post objects](#the-post-object) without `body`, each with `url` |
| total  | integer | Number of posts matching the filter, ignoring paging |
| limit  | integer | Limit applied |
| offset | integer | Offset applied |

**Use cases**

- "What drafts do I have?"
- Paging through everything with `offset` until `offset + limit >= total`.

---

## update\_post

Change a post. Any field left empty is not modified, and at least one field must be given.

**Parameters**

| Parameter  | Type         | Required | Default | Description |
|------------|--------------|----------|---------|-------------|
| slug       | string       | yes      | —       | Slug of the post to change. |
| title      | string       | no       | `""`    | New title. |
| body       | string       | no       | `""`    | New full Markdown body, replacing the old one. |
| summary    | string       | no       | `""`    | New summary. |
| tags       | list[string] | no       | `[]`    | New complete tag list, replacing the old one. Empty leaves tags unchanged. |
| clear_tags | boolean      | no       | `false` | Remove all tags. Ignored when `tags` is given. |
| new_slug   | string       | no       | `""`    | New URL slug. The old address stops working. |

**Returns**

The updated [post object](#the-post-object) including `body` and `url`.

**Use cases**

- Rewriting a draft after feedback.
- Retagging a post. To change only a sentence, prefer [replace\_in\_post](#replace_in_post).

---

## replace\_in\_post

Find and replace text in a post's body, so a small edit to a long post does not require sending the whole post again.

**Parameters**

| Parameter   | Type    | Required | Default | Description |
|-------------|---------|----------|---------|-------------|
| slug        | string  | yes      | —       | Slug of the post to change. |
| find        | string  | yes      | —       | Exact text to look for (case-sensitive). |
| replace     | string  | yes      | —       | Replacement text. Empty deletes the matched text. |
| replace_all | boolean | no       | `false` | Replace every occurrence. |

**Returns**

The updated [post object](#the-post-object) including `body` and `url`, plus `replacements` (the number of occurrences replaced).

The call fails, and the post is left unchanged, if `find` is not present, or if it appears more than once and `replace_all` is false. Include surrounding words in `find` to make it unique.

---

## publish\_post

Publish a draft so it appears on the blog's home page.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| slug      | string | yes      | Slug of the post to publish. |

**Returns**

The updated [post object](#the-post-object) with `status` `"published"`. `published_at` is set the first time and kept on later republishing.

---

## unpublish\_post

Return a published post to draft so it leaves the home page. The post is still viewable by direct address behind the password.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| slug      | string | yes      | Slug of the post to unpublish. |

**Returns**

The updated [post object](#the-post-object) with `status` `"draft"`.

---

## delete\_post

Permanently delete a post. This cannot be undone; use [unpublish\_post](#unpublish_post) to hide a post instead.

**Parameters**

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| slug      | string | yes      | Slug of the post to delete. |

**Returns**

| Field   | Type    | Description |
|---------|---------|-------------|
| slug    | string  | The slug requested |
| deleted | boolean | `false` if no such post existed |

---

## search\_posts

Search titles, summaries, bodies, and tags. Matching is case-insensitive (including non-ASCII letters), and every word in the query must appear somewhere in the post.

**Parameters**

| Parameter | Type    | Required | Default | Description |
|-----------|---------|----------|---------|-------------|
| query     | string  | yes      | —       | Words to look for (at most 8 are used). |
| status    | string  | no       | `"all"` | `"all"`, `"draft"`, or `"published"`. |
| limit     | integer | no       | `20`    | Posts to return, 1–50. |

**Returns**

| Field | Type    | Description |
|-------|---------|-------------|
| query | string  | The query as given |
| posts | list    | [Post objects](#the-post-object) without `body`, each with `url` and a `snippet` of text around the first match |
| count | integer | Number of posts returned |

---

## list\_tags

List every tag with the number of posts using it, most used first.

**Parameters**

| Parameter | Type   | Required | Default | Description |
|-----------|--------|----------|---------|-------------|
| status    | string | no       | `"all"` | Count only `"draft"` or `"published"` posts. |

**Returns**

| Field | Type    | Description |
|-------|---------|-------------|
| tags  | list    | Objects with `tag` and `count` |
| count | integer | Number of distinct tags |

---

## get\_blog\_info

Get the blog's title, viewer address, storage location, and post counts. Takes no parameters.

**Returns**

| Field           | Type   | Description |
|-----------------|--------|-------------|
| title           | string | Blog title |
| description     | string | Blog tagline |
| viewer_url      | string | Address of the viewer |
| viewer_username | string | Login name |
| password_source | string | `"BLOG_PASSWORD"`, or the path of the file holding the generated password |
| data_dir        | string | Where the database lives |
| posts           | object | `total`, `published`, `drafts`, and `tags` counts |

The password itself is never returned. Read it from the file named in `password_source`, or from your `.env`.

---

## The Post Object

| Field        | Type         | Description |
|--------------|--------------|-------------|
| slug         | string       | Identifier used by every other tool and in the address |
| title        | string       | Post title |
| status       | string       | `"draft"` or `"published"` |
| tags         | list[string] | Tags, alphabetical |
| summary      | string       | The explicit summary, or an excerpt of the opening paragraphs |
| word_count   | integer      | Words in the body, not counting Markdown syntax |
| created_at   | string       | UTC timestamp, e.g. `2026-11-27T14:30:00Z` |
| updated_at   | string       | UTC timestamp of the last change |
| published_at | string/null  | UTC timestamp of first publication; `null` if never published |
| body         | string       | Markdown source (only from tools that return full posts) |
| url          | string       | Viewer address of the post; requires the viewer password |

---

## Error Handling

Invalid input, a missing post, or a name conflict makes the tool call fail with a short message the model can act on, for example:

| Situation | Message |
|-----------|---------|
| Unknown slug | `Post 'x' not found` |
| Blank title | `title must not be empty` |
| Slug already used | `Slug 'x' is already in use` |
| Ambiguous `find` | `The text appears 2 times; add surrounding context to make it unique or set replace_all` |
| Bad `status` | `status must be 'all', 'draft', or 'published'` |
| `update_post` with no changes | `Nothing to update: pass at least one field to change` |

Failures never partly apply: a rejected create or update leaves the blog exactly as it was.
