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

### Yahoo Finance MCP (`yfinance_mcp/`)
FastMCP server exposing Yahoo Finance data as MCP tools. No API key required.
- Real-time quotes, market summary, market status
- Historical OHLCV data with configurable intervals
- Symbol search
- Company profiles, income statements, balance sheets, earnings
- Analyst price targets and recommendations
- Options chains and news

### Web MCP (`web_mcp/`)
FastMCP server for web search and URL fetching. No API key required.
- Web search via a local self-managed SearXNG instance (auto-installs on first run)
- News search with time filtering
- URL fetch with content extraction (Markdown, text, or raw HTML)
- Queries multiple engines simultaneously: Google, Bing, Brave, DuckDuckGo, Startpage, and more

### Android MCP (`android_mcp/`)
FastMCP server for controlling an Android device via ADB. Screenshots are served over HTTPS for vision model analysis.
- Shell commands, UI interaction (tap, swipe, type, key press), UI hierarchy dump
- App management (install, uninstall, launch, stop, list, clear data)
- Screenshot capture with compression, served via built-in HTTPS file server
- Device info, file push/pull, screen wake/state

**Requirements**: `adb` and `openssl` on PATH, connected Android device with USB debugging enabled

### Shell MCP (`shell_mcp/`)
FastMCP server for shell execution and file operations over SSH. Optionally auto-provisions a VirtualBox VM (Debian 13) as an isolated sandbox.
- Execute commands, read/write files, upload/download via SFTP
- List directories, get system info (memory, disk, uptime)
- Fetch generated files via a local HTTP URL
- Auto-creates and manages a Debian VM if VirtualBox is installed; otherwise connects to any SSH host

**Requirements**: SSH-accessible target, or VirtualBox with `vboxmanage` on PATH

### Docker Shell MCP (`docker_shell_mcp/`)
Docker-backed version of Shell MCP with the same command and file tools, using
an auto-managed Ubuntu container instead of SSH or VirtualBox.
- Persistent named workspace volume with configurable CPU, memory, PID, user, and network settings
- Auto-builds the sandbox image on first launch and reuses the container later
- Copies files through the Docker CLI and serves generated files over local HTTP

**Requirements**: Docker CLI and a running Docker daemon

### Subagent MCP (`subagent_mcp/`)
FastMCP server for delegating tasks to local LLM sub-agents via LM Studio or any OpenAI-compatible endpoint.
- Named agents with persistent system prompts, per-agent model selection, and MCP server access
- Agentic tool-use loop: agents can use tools from other MCP servers (web search, shell, Android, etc.)
- Parallel execution across multiple models or agents with auto-calibrated concurrency
- Multi-turn conversations with history tracking
- MCP server pool with `.env` pre-registration and runtime management

**Requirements**: OpenAI-compatible endpoint with Responses API support (e.g. LM Studio)

### WebShell MCP (`webshell_mcp/`)
Combined FastMCP server: sandboxed shell execution + web search and fetching, all in one VM. SearXNG runs inside the VM as a systemd service.
- All shell tools: execute commands, read/write files, upload/download via SFTP, system info, file serving
- All web tools: SearXNG web/news search, URL fetch with content extraction
- Auto-provisions a dedicated VM (`ai-webshell`) with SearXNG installed and running on first launch

**Requirements**: VirtualBox with `vboxmanage` on PATH, or an SSH target with SearXNG already running

### Fire TV MCP (`firetv_mcp/`)
FastMCP server for controlling Amazon Fire TV devices via ADB over WiFi.
- D-pad navigation, media playback control, volume, now-playing info
- App management with 30+ friendly aliases (netflix, prime, disney+, etc.), deep linking, sideloading
- Content search, open settings sections directly
- Screenshot capture served via HTTPS, screen recording, UI hierarchy dump
- Device info, network info, storage, brightness, bluetooth, reboot
- Auto-discovers Fire TV on the network if no IP is configured

**Requirements**: `adb` and `openssl` on PATH, ADB debugging enabled on Fire TV

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
- Pull requests and pushes to `main` test each packaged MCP server independently in GitHub Actions
