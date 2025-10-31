"""FastMCP server exposing RapidAPI news and local business tools."""

from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
from servers.base import build_server
from rapidapi_tools import (
    get_business_details,
    get_business_reviews,
    get_full_story_coverage,
    get_headlines,
    get_local_headlines,
    local_business_search,
    search_news,
)

from .base import build_server

INSTRUCTIONS = (
    "This server wraps the Tyumi RapidAPI news and local business integrations. "
    "Ensure RAPIDAPI_KEY is configured via environment or .env prior to launch."
)

server = build_server(
    "rapidapi-news",
    INSTRUCTIONS,
    [
        (search_news, "search_news", "Search Real-Time News Data articles."),
        (get_headlines, "get_headlines", "Retrieve top news headlines."),
        (get_local_headlines, "get_local_headlines", "Retrieve local news headlines."),
        (
            get_full_story_coverage,
            "get_full_story_coverage",
            "Retrieve coverage for a Real-Time News Data story.",
        ),
        (
            local_business_search,
            "local_business_search",
            "Search for local businesses using Local Business Data.",
        ),
        (
            get_business_details,
            "get_business_details",
            "Retrieve Local Business Data details for a business.",
        ),
        (
            get_business_reviews,
            "get_business_reviews",
            "Retrieve Local Business Data reviews for a business.",
        ),
    ],
)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9407


def run_server(*, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Run the news server using the HTTP transport."""

    server.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    run_server()
