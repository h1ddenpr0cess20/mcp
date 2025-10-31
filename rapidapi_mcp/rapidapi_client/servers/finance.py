"""FastMCP server exposing RapidAPI finance tools."""

from __future__ import annotations

from .base import build_server
from ..rapidapi_tools import get_twelve_data_price, get_twelve_data_quote

INSTRUCTIONS = (
    "This server wraps the Tyumi RapidAPI finance integrations. Ensure RAPIDAPI_KEY "
    "is configured (environment or .env) before launching."
)

server = build_server(
    "rapidapi-finance",
    INSTRUCTIONS,
    [
        (get_twelve_data_price, "twelve_data_price", "Retrieve the latest price for a symbol from Twelve Data."),
        (get_twelve_data_quote, "twelve_data_quote", "Retrieve quote information for a symbol from Twelve Data."),
    ],
)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9402


def run_server(*, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Run the finance server using the HTTP transport."""

    server.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    run_server()
