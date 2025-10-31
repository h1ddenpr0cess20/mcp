# RapidAPI MCP Server (FastMCP)

This project wraps the RapidAPI integrations from the [Tyumi](https://github.com/h1ddenpr0cess20/Tyumi) app as FastMCP domain servers. Each domain groups related tools (jobs, finance, food, entertainment, social, real estate, news, search) behind a dedicated FastMCP instance.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Start one of the domain servers (jobs, finance, food, entertainment, social, realestate, news, search)
python server.py jobs
```

To launch every domain server at once (each on its default port):

```bash
python server.py --all
```

Use `--host`/`--port` when starting an individual server if you need different bindings.

## Configuration

You need a **RapidAPI key** (`RAPIDAPI_KEY`) with access to the underlying APIs.

### Environment Variables
```bash
export RAPIDAPI_KEY="your_rapidapi_key"
```

### .env File (Optional)
Copy the provided example and populate your key:
```bash
cp .env.example .env
```
Edit `.env` and set `RAPIDAPI_KEY` accordingly. The client automatically loads the file via `python-dotenv`.

## Domain Servers & Default Ports

| Domain        | Summary of tools                                                           | Default port |
| ------------- | -------------------------------------------------------------------------- | ------------ |
| `jobs`        | Job searching and detail lookups via JSearch                               | 9401         |
| `finance`     | Twelve Data price & quote endpoints                                        | 9402         |
| `food`        | Recipe search against the Tasty API                                        | 9403         |
| `entertainment` | IMDB metadata, Steam catalog, Spotify artist and album lookups           | 9404         |
| `social`      | Twitter154 integrations for profiles, tweets, searches, and trends         | 9405         |
| `realestate`  | Zillow-powered rental search and property details                          | 9406         |
| `news`        | Real-Time News Data search, top headlines, and story coverage               | 9407         |
| `search`      | Real-Time Web Search plus Local Business Data lookups and reviews           | 9408         |

See `docs/domain_servers.md` for the full list of endpoints exposed per domain.

## Code Structure

- `server.py` – command-line launcher for individual or all domain servers.
- `rapidapi_client/rapidapi_tools/` – typed wrappers around each RapidAPI integration.
- `rapidapi_client/servers/` – FastMCP server definitions built on the shared helper in `servers/base.py`.
- `docs/` – additional notes, including endpoint inventories and provider documentation.

## Notes

- Servers run using the FastMCP HTTP transport so they can be independently bound to local ports.
- Tools share the `RapidAPIClient` helper which automatically injects the required RapidAPI headers.
- Contributions are welcome—add new integrations in `rapidapi_client/rapidapi_tools/` and register them in the appropriate domain server.
