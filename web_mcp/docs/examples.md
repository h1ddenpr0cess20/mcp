# Usage Examples

Practical workflows showing how to use the Web MCP server. Each scenario includes sample questions you can ask an AI assistant connected to this server.

---

## Table of Contents

- [Basic Web Search](#basic-web-search)
- [Filtered and Targeted Search](#filtered-and-targeted-search)
- [News Search](#news-search)
- [Fetching a URL](#fetching-a-url)
- [Search Then Fetch](#search-then-fetch)
- [Sample Questions for an AI Assistant](#sample-questions-for-an-ai-assistant)

---

## Basic Web Search

**Goal:** Find web pages on a topic.

**Tool call:**

```
web_search("python asyncio tutorial")
```

Returns up to 10 results with titles, URLs, and excerpts from multiple search engines.

**Sample prompts to an AI assistant:**

> Search the web for the best Python asyncio tutorials.

> What are the top results for "FastMCP getting started"?

> Find documentation pages for the httpx library.

---

## Filtered and Targeted Search

**Goal:** Use search operators or filters to narrow results.

**By site:**

```
web_search("site:github.com fastmcp examples")
```

**By time range:**

```
web_search("python 3.13 features", time_range="month")
```

**By category:**

```
web_search("large language models", categories="science", max_results=5)
```

**Sample prompts to an AI assistant:**

> Search GitHub for FastMCP example projects.

> Find recent blog posts about Rust from the last week.

> Look for academic papers about transformer models.

> Search for Python job postings on LinkedIn.

---

## News Search

**Goal:** Get recent news on a topic.

**Tool call:**

```
news_search("artificial intelligence regulation")
```

Defaults to results from the past week. Adjust with `time_range`:

```
news_search("OpenAI", time_range="day")
```

**Sample prompts to an AI assistant:**

> What's in the news about AI regulation this week?

> Find the latest news about Anthropic.

> What happened with the US stock market today?

> Search for recent news about the Python programming language.

---

## Fetching a URL

**Goal:** Read the full content of a specific page.

**Tool call:**

```
fetch_url("https://docs.python.org/3/library/asyncio.html")
```

Returns the page title and extracted main content as Markdown, stripping navigation, ads, and boilerplate.

**Plain text output:**

```
fetch_url("https://example.com/article", output_format="text")
```

**Without links:**

```
fetch_url("https://example.com/article", include_links=False)
```

**Sample prompts to an AI assistant:**

> Fetch the Python asyncio documentation and summarise the key concepts.

> Read this article and give me the main points: https://example.com/article

> Get the content of the FastMCP README from GitHub.

---

## Search Then Fetch

**Goal:** Find a relevant page and then read its full content.

**Typical sequence:**

1. `web_search("MCP server python tutorial")` — find candidate pages
2. `fetch_url("https://...")` — read the most relevant result in full

**Sample prompts to an AI assistant:**

> Search for FastMCP documentation, then fetch and summarise the most relevant page.

> Find the Wikipedia article about the MCP protocol and read it.

> Search for Python packaging best practices and read the top result.

> Look up the httpx changelog and fetch it so I can see what changed in the latest release.

---

## Sample Questions for an AI Assistant

**Research**
- Search the web for recent developments in quantum computing.
- What does the latest Python release include? Search for it and read the release notes.
- Find and summarise the top Stack Overflow answers about Python type hints.

**Current events**
- What's the top tech news today?
- Search for news about space exploration from the past week.
- What are people saying about the latest iPhone release?

**Technical lookup**
- Find the official documentation for the `httpx` library and summarise the async API.
- Search GitHub for open source MCP server implementations.
- Look up the FastMCP changelog and tell me what changed in recent versions.

**Content reading**
- Fetch https://peps.python.org/pep-0703/ and explain what it proposes.
- Read the Anthropic usage policy page and summarise the key points.
- Fetch the README from a GitHub repo and explain what the project does.
