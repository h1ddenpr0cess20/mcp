"""FastMCP server exposing RapidAPI news tools."""

from __future__ import annotations

from .base import build_server
from ..rapidapi_tools import get_full_story_coverage, get_headlines, get_local_headlines, search_news

INSTRUCTIONS = (
    "This server wraps the Tyumi RapidAPI news integrations powered by Real-Time News Data. "
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
    ],
)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9407


def run_server(*, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Run the news server using the HTTP transport."""

    server.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    run_server()
