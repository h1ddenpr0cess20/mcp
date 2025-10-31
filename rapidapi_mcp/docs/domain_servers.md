# Domain Server Reference

Each FastMCP domain server wraps a curated set of RapidAPI integrations and
exposes them over HTTP. Use this guide when you need to remember which tools
are available, what they do, and how to run them locally.

## Quick Matrix

| Domain | Default Port | Primary Capabilities | Backing Modules |
| ------ | ------------ | -------------------- | --------------- |
| `jobs` | 9401 | Searches open roles, salary info, and filters by location or remote status. | `rapidapi_client/servers/jobs.py`, `rapidapi_client/rapidapi_tools/jobs.py` |
| `finance` | 9402 | Retrieves real-time price and quote data from Twelve Data. | `rapidapi_client/servers/finance.py`, `rapidapi_client/rapidapi_tools/finance.py` |
| `food` | 9403 | Surfaces recipes, ingredient lists, and cooking instructions. | `rapidapi_client/servers/food.py`, `rapidapi_client/rapidapi_tools/food.py` |
| `entertainment` | 9404 | Combines film, TV, game, and music discovery in one endpoint. | `rapidapi_client/servers/entertainment.py`, `rapidapi_client/rapidapi_tools/entertainment.py` |
| `social` | 9405 | Fetches recent social posts and profile summaries. | `rapidapi_client/servers/social.py`, `rapidapi_client/rapidapi_tools/social.py` |
| `realestate` | 9406 | Provides property details, pricing trends, and nearby businesses. | `rapidapi_client/servers/realestate.py`, `rapidapi_client/rapidapi_tools/realestate.py` |
| `news` | 9407 | Streams the latest headlines, sorted by topic or publication. | `rapidapi_client/servers/news.py`, `rapidapi_client/rapidapi_tools/news.py` |
| `search` | 9408 | Runs general web search and powers local business discovery. | `rapidapi_client/servers/search.py`, `rapidapi_client/rapidapi_tools/search.py` |

## Running a Single Server

```bash
python server.py <domain>
```

- Use `--host` and `--port` to override defaults when launching one server.
- Each server logs the final URL on startup; watch the console for confirmation.

## Running the Orchestrator

```bash
python server.py --all
```

The orchestrator forks one process per domain using the ports listed above.
`--host` is the only override accepted in this mode. Stop the orchestrator with
`Ctrl+C`; it will terminate child processes for you.

## Adding a New Domain

1. Create a module under `rapidapi_client/rapidapi_tools/` that wraps the RapidAPI
   endpoints you intend to expose.
2. Add a server definition under `rapidapi_client/servers/` that maps FastMCP tools to
   the wrapper functions.
3. Register the new server in `server.py` with a unique port.
4. Document the upstream subscription in `data_providers.md` so the team knows
   which RapidAPI product to enable.
