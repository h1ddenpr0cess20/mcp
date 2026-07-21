"""FastMCP server exposing RapidAPI job search tools."""

from __future__ import annotations

from .base import build_server
from ..rapidapi_tools import get_job_details, search_jobs

INSTRUCTIONS = (
    "This server wraps the RapidAPI job search integrations from the Tyumi application. "
    "Configure the RAPIDAPI_KEY environment variable (or .env file) before starting."
)

server = build_server(
    "rapidapi-jobs",
    INSTRUCTIONS,
    [
        (search_jobs, "search_jobs", "Search for job listings via JSearch."),
        (get_job_details, "get_job_details", "Fetch details for a JSearch job posting."),
    ],
)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9401


def run_server(*, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, force_http: bool = False) -> None:
    """Run the jobs server. HTTP if launched directly or force_http, stdio if piped."""
    import sys
    if force_http or sys.stdin.isatty():
        from rapidapi_client.http_compat import serve_http

        serve_http(server, host=host, port=port, path="/mcp")
    else:
        server.run()


if __name__ == "__main__":
    run_server()
