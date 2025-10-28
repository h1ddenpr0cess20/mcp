# Last.fm MCP Server (FastMCP)

This project exposes **every Last.fm API method** listed on https://www.last.fm/api as MCP tools using **FastMCP**.
Tools are separated by type (album, artist, auth, chart, geo, library, tag, track, user).

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python server.py  # runs an MCP server; see FastMCP docs for client hookup
```

## Demo Script

Try the interactive demo to explore Last.fm API functionality:

```bash
# Install dependencies
pip install -e .

# Run the demo
python demo_lastfm.py

# Or use the command line shortcut
lastfm-demo
```

The demo showcases:
- Artist information and similar artists
- Track details and similar tracks
- Album information and track listings
- User profiles and listening history
- Global charts and popularity metrics
- Search functionality across artists, albums, and tracks

See `demo_README.md` for detailed usage instructions.

## Configuration

You’ll need a Last.fm **API key** (and secret for write/auth methods). Set via:

### Environment Variables
```bash
export LASTFM_API_KEY="your_api_key_here"
export LASTFM_API_SECRET="your_api_secret_here"  # optional
export LASTFM_SESSION_KEY="your_session_key_here"  # optional
```

### .env File (Recommended)
Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
# Edit .env with your API credentials
```

### API Keys
- **API Key**: Required for all API calls
  - Get one at: https://www.last.fm/api/account/create (free, instant)
- **API Secret**: Required for authenticated operations (scrobbling, loving tracks)
- **Session Key**: Obtained through authentication flow (for user-specific operations)

## Notes

- Read endpoints use GET; write endpoints (e.g., addTags, love, scrobble) use signed POST with `api_sig`.
- Each tool accepts parameters that mirror the Last.fm docs.
- See `lastfm_client/client.py` for the API classes grouped by type.
- See `server.py` for FastMCP tool registrations.
