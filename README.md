# MCP Servers Collection

A collection of Model Context Protocol (MCP) servers built with FastMCP, each serving different APIs and data sources.

## Available Servers

### Last.fm MCP (`lastfm_mcp/`)
FastMCP server exposing the entire Last.fm API as MCP tools. Categories include:
- Artist information, similar artists, top tracks/albums
- Album metadata and tracks
- Track details, similar tracks, love/scrobble functionality
- User profiles, listening history, charts
- Global charts, geo-specific data
- Tag-based content and search

**Requirements**: Last.fm API key (free from https://www.last.fm/api)

### Grokipedia MCP (`grokipedia_mcp/`)
FastMCP server for scraping and structuring content from Grokipedia pages.

**Features**:
- Scrape page content into structured sections with headings and text blocks
- Web scraping using BeautifulSoup
- Clean separation between scraping logic and MCP server

### RapidAPI MCP (`rapidapi_mcp/`)
Suite of FastMCP servers wrapping the RapidAPI integrations used in the [Tyumi](http://github.com/h1ddenpr0cess20/Tyumi) project. Each domain (jobs, finance, food, entertainment, social, real estate, news, search) runs as a separate FastMCP instance.

**Requirements**: RapidAPI key (`RAPIDAPI_KEY` environment variable or `.env`)

## Common Setup
Each server follows a similar structure:
```
package_name/
├── pyproject.toml      # Modern Python packaging
├── requirements.txt    # Dependencies
├── server.py          # FastMCP server and tool definitions
├── README.md          # Server-specific documentation
└── client_lib/        # Core business logic
    ├── __init__.py
    └── client.py      # API/scraping implementation
```

## Running Servers
```bash
# Example for Grokipedia MCP
cd grokipedia_mcp
python -m venv .venv && source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python server.py  # Launches MCP server for client integration
```

See individual server READMEs for specific setup instructions and configuration.

## Development
- Built with FastMCP for MCP compatibility
- Clean architecture with separation of concerns
- Python 3.9+ required
- Each server can be used as a standalone package
