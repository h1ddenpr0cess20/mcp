# RapidAPI FastMCP Server Documentation

Welcome to the living knowledge base for the FastMCP RapidAPI integrations.
These documents expand on the top-level project README with deeper context,
operational notes, and quick references for the service owners and
contributors.

## How to Use These Docs

- Start with `data_providers.md` to understand which upstream APIs back each
  toolset and where to enable them on RapidAPI.
- Jump to `domain_servers.md` when you need a refresher on the domain apps,
  their responsibilities, and the ports they listen on by default.
- Visit `tests/` (when present) for unit tests that lock in CLI behavior and
  multiprocessing orchestration.
- Add new pages whenever you integrate a new vertical or learn something
  worth sharing—keeping the documentation accurate is part of the review
  checklist.

### Style Notes

- Prefer short sections with task-focused headings.
- Document surprises: non-obvious parameters, rate limits, or error modes.
- Keep examples runnable; indicate required environment variables explicitly.
