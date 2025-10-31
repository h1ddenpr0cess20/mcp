"""Client library backing the RapidAPI MCP servers."""

from .rapidapi_tools import MissingRapidAPIKeyError, RapidAPIClient

__all__ = ["MissingRapidAPIKeyError", "RapidAPIClient"]
