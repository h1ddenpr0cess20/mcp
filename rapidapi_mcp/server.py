"""Convenience launcher for domain-specific FastMCP servers."""

from __future__ import annotations

import argparse
import multiprocessing as mp
from typing import Callable, Dict, List, Tuple

from fastmcp import FastMCP

from rapidapi_client.servers import (
    entertainment,
    finance,
    food,
    jobs,
    news,
    search,
    realestate,
    social,
)

ENTERTAINMENT_HOST = entertainment.DEFAULT_HOST
ENTERTAINMENT_PORT = entertainment.DEFAULT_PORT
entertainment_server = entertainment.server
run_entertainment_server = entertainment.run_server

FINANCE_HOST = finance.DEFAULT_HOST
FINANCE_PORT = finance.DEFAULT_PORT
finance_server = finance.server
run_finance_server = finance.run_server

FOOD_HOST = food.DEFAULT_HOST
FOOD_PORT = food.DEFAULT_PORT
food_server = food.server
run_food_server = food.run_server

JOBS_HOST = jobs.DEFAULT_HOST
JOBS_PORT = jobs.DEFAULT_PORT
jobs_server = jobs.server
run_jobs_server = jobs.run_server

NEWS_HOST = news.DEFAULT_HOST
NEWS_PORT = news.DEFAULT_PORT
news_server = news.server
run_news_server = news.run_server

SEARCH_HOST = search.DEFAULT_HOST
SEARCH_PORT = search.DEFAULT_PORT
search_server = search.server
run_search_server = search.run_server

REALESTATE_HOST = realestate.DEFAULT_HOST
REALESTATE_PORT = realestate.DEFAULT_PORT
realestate_server = realestate.server
run_realestate_server = realestate.run_server

SOCIAL_HOST = social.DEFAULT_HOST
SOCIAL_PORT = social.DEFAULT_PORT
social_server = social.server
run_social_server = social.run_server

ServerEntry = Tuple[FastMCP, Callable[..., None], str, int]

SERVERS: Dict[str, ServerEntry] = {
    "entertainment": (entertainment_server, run_entertainment_server, ENTERTAINMENT_HOST, ENTERTAINMENT_PORT),
    "finance": (finance_server, run_finance_server, FINANCE_HOST, FINANCE_PORT),
    "food": (food_server, run_food_server, FOOD_HOST, FOOD_PORT),
    "jobs": (jobs_server, run_jobs_server, JOBS_HOST, JOBS_PORT),
    "news": (news_server, run_news_server, NEWS_HOST, NEWS_PORT),
    "search": (search_server, run_search_server, SEARCH_HOST, SEARCH_PORT),
    "realestate": (realestate_server, run_realestate_server, REALESTATE_HOST, REALESTATE_PORT),
    "social": (social_server, run_social_server, SOCIAL_HOST, SOCIAL_PORT),
}

__all__ = ["SERVERS"]


def run_all_servers(*, host: str | None = None) -> None:
    """Run all domain servers concurrently using separate processes."""

    processes: List[Tuple[str, mp.Process]] = []
    try:
        for name, (_, runner, default_host, default_port) in SERVERS.items():
            bound_host = host or default_host
            process = mp.Process(
                target=runner,
                name=f"{name}-server",
                kwargs={"host": bound_host, "port": default_port},
            )
            process.start()
            processes.append((name, process))
            print(f"[{name}] Serving on {bound_host}:{default_port} (pid={process.pid})", flush=True)

        for _, process in processes:
            process.join()
    except KeyboardInterrupt:
        print("\nStopping all RapidAPI FastMCP servers...", flush=True)
    finally:
        for name, process in processes:
            if process.is_alive():
                process.terminate()
                print(f"[{name}] Terminated.", flush=True)
        for _, process in processes:
            process.join()


def main() -> None:
    """Run a selected domain server."""

    parser = argparse.ArgumentParser(
        description=(
            "Run one of the domain-specific RapidAPI FastMCP servers. "
            "Available domains: %(choices)s"
        )
    )
    parser.add_argument("domain", nargs="?", choices=sorted(SERVERS), help="Domain server to launch.")
    parser.add_argument("--all", action="store_true", help="Launch every domain server concurrently.")
    parser.add_argument("--host", default=None, help="Host interface to bind (default per server).")
    parser.add_argument("--port", type=int, default=None, help="Port to bind (default per server).")
    args = parser.parse_args()

    if args.all and args.domain:
        parser.error("Specify either a domain or --all, not both.")

    if not args.all and not args.domain:
        parser.error("Choose a domain to launch or pass --all to run every server.")

    if args.all:
        if args.port is not None:
            parser.error("--port cannot be combined with --all because each server has an explicit port.")
        run_all_servers(host=args.host)
        return

    server, runner, default_host, default_port = SERVERS[args.domain]
    host = args.host or default_host
    port = args.port or default_port
    runner(host=host, port=port)


if __name__ == "__main__":
    mp.freeze_support()
    main()
