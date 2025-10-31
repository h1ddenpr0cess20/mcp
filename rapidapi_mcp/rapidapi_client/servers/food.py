"""FastMCP server exposing RapidAPI food tools."""

from __future__ import annotations

from .base import build_server
from ..rapidapi_tools import search_recipes

INSTRUCTIONS = (
    "This server exposes the Tyumi RapidAPI food integrations. Configure RAPIDAPI_KEY "
    "in the environment or .env before starting."
)

server = build_server(
    "rapidapi-food",
    INSTRUCTIONS,
    [
        (search_recipes, "search_recipes", "Search for recipes using Tasty."),
    ],
)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9403


def run_server(*, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Run the food server using the HTTP transport."""

    server.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    run_server()
