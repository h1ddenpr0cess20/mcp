# Usage Examples

Practical workflows showing how to use the Grokipedia MCP server for common research and information tasks. Each scenario includes sample questions you can ask an AI assistant connected to this server.

---

## Table of Contents

- [Look Up a Person](#look-up-a-person)
- [Research a Concept or Topic](#research-a-concept-or-topic)
- [Extract Structured Facts](#extract-structured-facts)
- [Research a Place or Organisation](#research-a-place-or-organisation)
- [Search for Pages](#search-for-pages)
- [Chaining Multiple Lookups](#chaining-multiple-lookups)
- [Sample Questions for an AI Assistant](#sample-questions-for-an-ai-assistant)

---

## Look Up a Person

**Goal:** Get a biographical summary of a notable person including key facts from their info panel.

**Tool call:**

```
scrape_grokipedia("Marie Curie")
```

The response will include:
- `content` — article sections covering early life, career, scientific work, legacy
- `info_panels` — structured fields such as Born, Died, Nationality, Known for, Awards

**Sample prompts to an AI assistant:**

> Tell me about Marie Curie — key facts and a brief summary of her scientific contributions.

> What nationality was Ada Lovelace and what is she known for? Check Grokipedia.

> Summarise the life of Nikola Tesla based on his Grokipedia page.

**What to look for:**
- The info panel `fields` array contains the most structured, scannable facts (dates, nationalities, occupations).
- The `content` sections give the narrative detail. Look for sections with lower `level` values (2 or 3) for the main biographical sections.

---

## Research a Concept or Topic

**Goal:** Get an explanation of a term, theory, or subject area.

**Tool call:**

```
scrape_grokipedia("Machine learning")
```

**Sample prompts to an AI assistant:**

> Explain machine learning to me using the Grokipedia article as your source.

> What does Grokipedia say about quantum computing? Give me the key sections.

> Look up "natural language processing" on Grokipedia and summarise what it covers.

> What is the greenhouse effect? Use the Grokipedia page to explain it clearly.

**Tips:**
- For multi-word topics, use the title as it likely appears on the page. Common capitalisation styles: `"World War II"`, `"French Revolution"`, `"Theory of relativity"`.
- If the page title is uncertain, try the most natural English phrasing. The URL pattern is `https://grokipedia.com/page/{title_with_underscores}` — if you can browse to a page manually, the title in the URL is exactly what to pass to the tool.

---

## Extract Structured Facts

**Goal:** Pull specific factual fields from a page without reading through the full prose.

**Tool call:**

```
scrape_grokipedia("Python (programming language)")
```

The `info_panels` list will contain fields like designer, first appeared, typing discipline, and license — without having to parse the article text.

**Sample prompts to an AI assistant:**

> What year was the Python programming language first released? Check the Grokipedia info panel.

> What are the key facts about the Eiffel Tower — height, year built, location?

> Look up "Mount Everest" and give me the structured facts from the info panel: height, first ascent, location.

> What are the official languages of Switzerland according to Grokipedia?

**Why info panels are useful:**
- They contain the same type of information as a reference card: dates, measurements, classifications, affiliations.
- They are parsed into label-value pairs, so an AI assistant can retrieve a specific field directly without reading all the article text.

---

## Research a Place or Organisation

**Goal:** Get an overview of a country, city, company, or institution.

**Tool call:**

```
scrape_grokipedia("Tokyo")
```

**Sample prompts to an AI assistant:**

> Give me a summary of Tokyo — population, geography, and significance.

> What does Grokipedia say about CERN? Cover what it is, where it is, and what it does.

> Look up "Amazon (company)" on Grokipedia and tell me when it was founded and what it does.

> Summarise the history of the United Nations from its Grokipedia page.

**Tips:**
- Company and organisation pages often have disambiguation in the title: `"Apple (company)"`, `"Amazon (company)"`.
- Country pages typically have rich info panels with capital, population, area, currency, and official languages.

---

## Search for Pages

**Goal:** Find Grokipedia pages related to a topic when you don't know the exact page title.

**Tool call:**

```
search_grokipedia("quantum")
```

The response will include a list of matching pages with titles, snippets, and URLs. You can then use `scrape_grokipedia` to fetch the full content of any result.

**Sample prompts to an AI assistant:**

> Search Grokipedia for articles about quantum computing.

> I'm looking for pages about the French Revolution on Grokipedia — search for them.

> Find all Grokipedia pages related to "machine learning" and list the top results.

**Paginating through results:**

```
search_grokipedia("quantum", page=2)
```

Each response includes `total_pages` so you know how many pages of results are available.

**Tips:**
- Use search to discover the correct page title before calling `scrape_grokipedia`. This avoids 404 errors from guessing titles.
- Search returns up to 12 results per page. Use the `page` parameter to browse further.

---

## Chaining Multiple Lookups

**Goal:** Compare or connect information across multiple Grokipedia pages.

**Tool sequence:**

1. `scrape_grokipedia("Albert Einstein")` — get Einstein's biography and key facts
2. `scrape_grokipedia("Theory of relativity")` — get the theory itself explained
3. `scrape_grokipedia("Nobel Prize in Physics")` — understand the award he received

**Sample prompts to an AI assistant:**

> Compare the Grokipedia articles on the French Revolution and the American Revolution. What do they have in common and how do they differ?

> Look up both "Charles Darwin" and "Natural selection" on Grokipedia, then explain how his life connects to the theory.

> I want to understand the history of the internet. Look up "ARPANET" and "World Wide Web" on Grokipedia and give me a connected timeline.

> Compare the Grokipedia pages for Rome and Athens — key historical periods, population, and significance.

**Why chaining works well:**
- Each call is fast and focused. Breaking a broad research question into specific page lookups keeps each response precise.
- Info panels across related pages often contain cross-referenced facts (birth/death dates, founding dates, locations) that an AI assistant can use to build a coherent summary.

---

## Sample Questions for an AI Assistant

The following questions illustrate what you can ask an AI assistant that has this MCP server connected. The assistant will call `search_grokipedia` or `scrape_grokipedia` on your behalf and synthesise the response.

**People**
- Who was Nikola Tesla and what is he known for?
- Summarise the life of Alan Turing.
- What nationality was Frida Kahlo and what art movement was she associated with?
- When was Mahatma Gandhi born and what was his role in Indian independence?

**Science and technology**
- What is quantum entanglement? Use the Grokipedia article to explain it simply.
- How does a black hole form? Look it up on Grokipedia.
- What programming paradigm does Haskell use?
- What does Grokipedia say about CRISPR?

**History and events**
- Give me the key facts about the French Revolution from Grokipedia.
- What caused World War I? Summarise the Grokipedia article.
- When was the Berlin Wall built and when did it fall?
- What happened during the Space Race?

**Places**
- What is the population and area of Brazil?
- What are the official languages of Belgium?
- Describe the geography of the Amazon River.
- What is Grokipedia's summary of the city of Istanbul?

**Organisations and institutions**
- What is the International Monetary Fund and when was it founded?
- What does NASA do and where is it based?
- When was the European Union established and how many member states does it have?
- What is the World Health Organization's mandate?

**Concepts and ideas**
- Explain supply and demand using the Grokipedia article.
- What is the scientific method?
- What does Grokipedia say about democracy as a concept?
- Summarise the philosophy of Stoicism.
