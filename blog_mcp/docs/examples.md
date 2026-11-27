# Usage Examples

Practical workflows showing how to use the Blog MCP server. Each scenario includes sample questions you can ask an AI assistant connected to this server.

---

## Table of Contents

- [Write and Review a Draft](#write-and-review-a-draft)
- [Publish a Quick Note](#publish-a-quick-note)
- [Make a Small Edit](#make-a-small-edit)
- [Find Old Posts](#find-old-posts)
- [Organize with Tags](#organize-with-tags)
- [Take a Post Down](#take-a-post-down)
- [A Private Journal with a Local Model](#a-private-journal-with-a-local-model)
- [Sample Questions for an AI Assistant](#sample-questions-for-an-ai-assistant)

---

## Write and Review a Draft

**Goal:** Have the assistant write a post, read it in the browser, then publish it.

**Tool call:**

```
create_post(
    title="Notes on Sourdough",
    body="# Notes on Sourdough\n\nMy starter finally doubled overnight...",
    tags=["baking", "notes"]
)
```

Returns the post with `status: "draft"` and a `url`. Open that address in your browser, sign in as `owner` with the password from `~/mcp-blog/viewer_password`, and read the draft there (it also appears under **Drafts**). When it looks right:

```
publish_post("notes-on-sourdough")
```

The post now appears on the home page.

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

If the text appears more than once the call fails and nothing changes; either include more surrounding words in `find`, or replace every occurrence:

```
replace_in_post("notes-on-sourdough", find="starter", replace="levain", replace_all=True)
```

For a larger rewrite, use `update_post` with the complete new `body`.

---

## Find Old Posts

**Goal:** Locate what you wrote about a topic.

```
search_posts("sourdough starter")
```

Every word must match, case-insensitively, in the title, summary, body, or tags. Each result includes a `snippet` with the text around the match and a `url`.

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
```

```
update_post("notes-on-sourdough", tags=["baking", "bread"])
update_post("old-post", clear_tags=True)
```

Tags are normalized, so `"Machine Learning"`, `"#machine learning"`, and `"machine-learning"` are the same tag. Each tag also has a page in the viewer, at `/tag/<name>`.

---

## Take a Post Down

**Goal:** Remove a post from the home page, or remove it entirely.

```
unpublish_post("notes-on-sourdough")   # back to draft; still viewable behind the password
delete_post("notes-on-sourdough")      # gone for good
```

`delete_post` cannot be undone. Back up `blog.db` first if you might want it back (see [Backups](configuration.md#backups)).

---

## A Private Journal with a Local Model

**Goal:** Keep everything on your own machine, including the text the model sees.

Posts are stored locally, but any hosted model you connect reads and writes them through its provider. To avoid that, register the blog with [`subagent_mcp`](../../subagent_mcp/README.md) and use a local model:

```
SUBAGENT_MCP_SERVERS=blog=http://127.0.0.1:9410/mcp
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

- "Write a draft post about what I learned this week, tagged `weekly`."
- "Show me all my drafts."
- "Publish the sourdough post."
- "In my post about the migration, change 'Friday' to 'Monday'."
- "Search my blog for anything mentioning the budget."
- "What tags do I use most?"
- "Move everything tagged `ideas` that I haven't published into a single summary post."
- "Unpublish the post about the trip; I want to rework it."
- "How many posts do I have, and where is my password stored?"
