# Tool Reference

Complete reference for all tools exposed by the Grokipedia MCP server.

---

## Table of Contents

- [scrape_grokipedia](#scrape_grokipedia)
- [Return Value Structure](#return-value-structure)
- [Error Handling](#error-handling)

---

## scrape_grokipedia

Fetches a Grokipedia page by title and returns its full content as structured data. The page HTML is parsed into two parallel representations: a flat list of content sections (headings and prose blocks) and a list of structured info panels (the sidebar-style fact boxes common on encyclopedia pages).

**Parameters**

| Parameter   | Type   | Required | Description                                          |
|-------------|--------|----------|------------------------------------------------------|
| page_title  | string | yes      | The page title as it appears in the Grokipedia URL, e.g. `"Elon Musk"` or `"Python (programming language)"` |

Spaces in the title are converted to underscores automatically before the URL is constructed. Capitalisation should match the page title as it appears on the site.

**URL pattern**

```
https://grokipedia.com/page/{page_title_with_underscores}
```

For example, `"Marie Curie"` fetches `https://grokipedia.com/page/Marie_Curie`.

**Returns**

A dictionary with the following top-level keys:

| Key          | Type             | Description                                              |
|--------------|------------------|----------------------------------------------------------|
| page_title   | string           | The title as passed in                                   |
| url          | string           | The full URL that was fetched                            |
| content      | list of objects  | Parsed article sections; see [Content sections](#content-sections) |
| info_panels  | list of objects  | Structured sidebar panels; see [Info panels](#info-panels) |

On a network or HTTP error, the response omits `content` and `info_panels` and instead returns:

| Key          | Type   | Description                            |
|--------------|--------|----------------------------------------|
| page_title   | string | The title as passed in                 |
| url          | string | The URL that was attempted             |
| error        | string | Human-readable description of the error |

**Use cases**

- Look up a person, place, concept, or event by name and retrieve a structured summary.
- Extract factual fields (birth date, nationality, occupation) from the info panel without parsing prose.
- Feed article sections into a summarisation or question-answering workflow.
- Retrieve the canonical Grokipedia URL for a given topic.

---

## Return Value Structure

### Content sections

`content` is a list of section objects. Each section corresponds to one heading in the article and contains the blocks of text that fall under it.

| Field    | Type            | Description                                                                 |
|----------|-----------------|-----------------------------------------------------------------------------|
| heading  | string or null  | The section heading text (e.g. `"Early life"`). Null for introductory text before the first heading. |
| level    | integer or null | Heading depth: 1 for `<h1>`, 2 for `<h2>`, etc. Null if no heading.        |
| blocks   | list of strings | Text content under this heading. Bullet list items are prefixed with `• `.  |

Example:

```json
{
  "heading": "Early life",
  "level": 2,
  "blocks": [
    "Marie Curie was born on 7 November 1867 in Warsaw.",
    "• Born: 7 November 1867",
    "• Nationality: Polish, French"
  ]
}
```

### Info panels

`info_panels` is a list of panel objects parsed from the `<aside>` elements on the page. These are the structured fact boxes that appear alongside the main article text.

Each panel object has the following fields:

| Field   | Type             | Description                                  |
|---------|------------------|----------------------------------------------|
| fields  | list of objects  | Key-value pairs extracted from the panel     |
| image   | object or absent | Image associated with the panel, if present  |

Each entry in `fields` has:

| Field  | Type            | Description                                          |
|--------|-----------------|------------------------------------------------------|
| label  | string          | The field name, e.g. `"Born"`, `"Nationality"`       |
| values | list of strings | One or more values for the field                     |

The `image` object, when present, has:

| Field   | Type             | Description                                   |
|---------|------------------|-----------------------------------------------|
| src     | string or null   | Absolute URL to the image file                |
| alt     | string or null   | The image alt text                            |
| caption | string or null   | Caption text from the associated `<figcaption>`, if any |

Example:

```json
{
  "fields": [
    {"label": "Born", "values": ["7 November 1867", "Warsaw, Congress Poland"]},
    {"label": "Died", "values": ["4 July 1934 (aged 66)", "Passy, Haute-Savoie, France"]},
    {"label": "Nationality", "values": ["Polish", "French"]}
  ],
  "image": {
    "src": "https://grokipedia.com/images/marie_curie.jpg",
    "alt": "Marie Curie",
    "caption": "Marie Curie, c. 1903"
  }
}
```

---

## Error Handling

If the page cannot be fetched (network timeout, HTTP 404, HTTP 500, etc.), the tool returns a dictionary with an `error` key instead of `content` and `info_panels`. The server does not raise an exception — it always returns a dict.

Example error response:

```json
{
  "page_title": "Nonexistent Page",
  "url": "https://grokipedia.com/page/Nonexistent_Page",
  "error": "Failed to fetch page: 404 Client Error: Not Found for url: ..."
}
```

When handling responses, check for the presence of the `error` key before attempting to access `content` or `info_panels`.
