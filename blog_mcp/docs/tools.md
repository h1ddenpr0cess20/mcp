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
- [upload\_image](#upload_image)
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

To change only a sentence, prefer [replace\_in\_post](#replace_in_post).

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

The updated [post object](#the-post-object), plus `replacements` (the number of occurrences replaced).

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

Return a published post to draft so it leaves the home page.

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

## upload\_image

Upload an image file from the computer this server runs on, so a post can show it. PNG, JPEG, GIF, and WebP up to 8 MB. The blog checks the file's contents, so a file that is not really an image is refused whatever it is called.

**Parameters**

| Parameter | Type   | Required | Default | Description |
|-----------|--------|----------|---------|-------------|
| file_path | string | yes      | —       | Path of the image on the machine running this server. `~` is expanded. |
| alt_text  | string | no       | `""`    | Short description for screen readers. |

**Returns**

| Field        | Type   | Description |
|--------------|--------|-------------|
| url          | string | The image's address on the blog, e.g. `/media/ab12….png` |
| absolute_url | string | The same with the blog's full address |
| markdown     | string | `![alt](url)`, ready to paste into a post body |

On a private blog the image is only visible to logged-in readers, like everything else.

---

## get\_blog\_info

Check the blog. Takes no parameters.

**Returns**

| Field       | Type    | Description |
|-------------|---------|-------------|
| blog_url    | string  | The blog's address |
| blog_running | boolean | Whether the blog answered |
| title       | string  | Blog title (when running) |
| description | string  | Tagline (when running) |
| public      | boolean | Whether visitors can read published posts without logging in (when running) |
| posts       | object  | `total`, `published`, `drafts`, and `tags` counts (when running) |
| message     | string  | Why the blog could not be reached (only when `blog_running` is false) |

This tool reports a blog that is down as an answer rather than failing. A rejected API token is still an error.

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
| version      | integer      | Starts at 1 and rises with every change |
| created_at   | string       | UTC timestamp, e.g. `2026-11-27T14:30:00Z` |
| updated_at   | string       | UTC timestamp of the last change |
| published_at | string/null  | UTC timestamp of first publication; `null` if never published |
| body         | string       | Markdown source (only from tools that return full posts) |
| url          | string       | The post's address on the blog |

---

## Error Handling

A problem makes the tool call fail with a short message the model can act on:

| Situation | Message |
|-----------|---------|
| Blog not running | `Cannot reach the blog at http://127.0.0.1:9901. Is it running? Start it with python blog/blog.py, or fix BLOG_URL.` |
| Wrong token | `The blog rejected the API token. Check BLOG_API_TOKEN against the blog's api_token.` |
| Unknown slug | `Post 'x' not found` |
| Blank title | `title must not be empty` |
| Slug already used | `Slug 'x' is already in use` |
| Ambiguous `find` | `The text appears 2 times; add surrounding context to make it unique or set replace_all` |
| `update_post` with no changes | `Nothing to update: pass at least one field to change` |
| Missing local file | `No file at /path/to/image.png` |
| Not an image | `Only PNG, JPEG, GIF, and WebP images can be uploaded` |

Failures never partly apply: a rejected create or update leaves the blog exactly as it was.
