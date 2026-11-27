# Usage Examples

Practical workflows showing how to use the Blog MCP server. Each scenario includes sample questions you can ask an AI assistant connected to this server.

---

## Table of Contents

- [Write and Review a Draft](#write-and-review-a-draft)
- [Publish a Quick Note](#publish-a-quick-note)
- [Make a Small Edit](#make-a-small-edit)
- [Add a Picture](#add-a-picture)
- [Find Old Posts](#find-old-posts)
- [Organize with Tags](#organize-with-tags)
- [Take a Post Down](#take-a-post-down)
- [Editing in the Browser at the Same Time](#editing-in-the-browser-at-the-same-time)
- [A Private Journal with a Local Model](#a-private-journal-with-a-local-model)
- [Sample Questions for an AI Assistant](#sample-questions-for-an-ai-assistant)

---

## Write and Review a Draft

**Goal:** Have the assistant write a post, read it on the blog, then publish it.

**Tool call:**

```
create_post(
    title="Notes on Sourdough",
    body="# Notes on Sourdough\n\nMy starter finally doubled overnight...",
    tags=["baking", "notes"]
)
```

Returns the post with `status: "draft"` and a `url`. Open that address, log in to the blog, and read the draft. You can also polish it in the blog's editor. When it looks right:

```
publish_post("notes-on-sourdough")
```

The post now appears on the blog's home page.

---

## Publish a Quick Note

**Goal:** Skip the draft step for something short.

```
create_post(
    title="Idea: weekly review",
    body="Spend Friday afternoon writing down what shipped.",
    tags=["ideas"],
    publish=True
)
```

---

## Make a Small Edit

**Goal:** Fix a typo or change one sentence without resending the post.

```
replace_in_post("notes-on-sourdough", find="doubled overnite", replace="doubled overnight")
```

If the text appears more than once the call fails and nothing changes; include more surrounding words in `find`, or replace every occurrence:

```
replace_in_post("notes-on-sourdough", find="starter", replace="levain", replace_all=True)
```

For a larger rewrite, use `update_post` with the complete new `body`.

---

## Add a Picture

**Goal:** Put an image from your computer into a post.

```
upload_image("~/Pictures/loaf.jpg", alt_text="The finished loaf")
```

Returns `markdown: "![The finished loaf](/media/….jpg)"`. Put that line in the post, for example with `replace_in_post` or `create_post`:

```
replace_in_post("notes-on-sourdough", find="Here is the result:", replace="Here is the result:\n\n![The finished loaf](/media/….jpg)")
```

---

## Find Old Posts

**Goal:** Locate what you wrote about a topic.

```
search_posts("sourdough starter")
```

Every word must match, case-insensitively, in the title, summary, body, or tags. Each result includes a `snippet` and a `url`.

To browse instead:

```
list_posts(status="published", limit=10)
list_posts(status="draft")
list_posts(tag="baking")
```

---

## Organize with Tags

**Goal:** See how the blog is organized and tidy it up.

```
list_tags(status="published")
update_post("notes-on-sourdough", tags=["baking", "bread"])
update_post("old-post", clear_tags=True)
```

Tags are normalized, so `"Machine Learning"`, `"#machine learning"`, and `"machine-learning"` are the same tag. Each tag also has a page on the blog.

---

## Take a Post Down

**Goal:** Remove a post from the home page, or remove it entirely.

```
unpublish_post("notes-on-sourdough")   # back to draft; still there for you in the editor
delete_post("notes-on-sourdough")      # gone for good
```

`delete_post` cannot be undone. Back up the blog first if you might want it back (see the blog's [backup notes](../blog/docs/configuration.md#backups)).

---

## Editing in the Browser at the Same Time

You can have a post open in the blog's editor while an assistant works on it. Every change bumps the post's version. If the assistant changes the post after you opened it and you then press Save, the blog refuses the save, shows a warning, and keeps your text in the form; saving again deliberately replaces the other version. Nothing is overwritten silently.

---

## A Private Journal with a Local Model

**Goal:** Keep the text on your own machine, including what the model sees.

The blog stores everything locally, but a hosted model you connect reads and writes posts through its provider. To avoid that, register this server with [`subagent_mcp`](../../subagent_mcp/README.md) and use a local model:

```
SUBAGENT_MCP_SERVERS=blog=http://127.0.0.1:9900/mcp
```

```
create_agent(
    name="journal",
    system_prompt="You help me keep a private journal. Save entries as drafts with sensible tags.",
    mcp_servers=["blog"]
)
ask_agent("journal", "Write up today's notes: fixed the flaky test, started the migration.")
```

---

## Sample Questions for an AI Assistant

- "Is my blog running?"
- "Write a draft post about what I learned this week, tagged `weekly`."
- "Show me all my drafts."
- "Publish the sourdough post."
- "In my post about the migration, change 'Friday' to 'Monday'."
- "Add this screenshot to the post about the release."
- "Search my blog for anything mentioning the budget."
- "What tags do I use most?"
- "Unpublish the post about the trip; I want to rework it."
