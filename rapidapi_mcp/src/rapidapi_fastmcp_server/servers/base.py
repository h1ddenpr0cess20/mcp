"""Shared helpers for constructing FastMCP servers."""

from __future__ import annotations

import sys
from pathlib import Path
import inspect
from typing import Any, Callable, Iterable, Tuple

from fastmcp import FastMCP

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.append(str(_PROJECT_ROOT))

ToolSpec = Tuple[Callable[..., Any], str, str]


def build_server(name: str, instructions: str, tool_specs: Iterable[ToolSpec]) -> FastMCP:
    """Create a :class:`FastMCP` server and register tool functions."""

    server = FastMCP(name, instructions=instructions)
    for func, tool_name, description in tool_specs:
        tool = server.tool(
            func,
            name=tool_name,
            description=description,
            exclude_args=["client"],
        )

        params_schema = tool.parameters
        required = set(params_schema.get("required", []))
        if not required:
            continue

        signature = inspect.signature(func)
        optional_params = {
            param_name
            for param_name, param in signature.parameters.items()
            if param.default is not inspect._empty
        }
        optional_params.add("client")

        updated_required = [name for name in required if name not in optional_params]
        if updated_required:
            params_schema["required"] = updated_required
        else:
            params_schema.pop("required", None)

    return server
