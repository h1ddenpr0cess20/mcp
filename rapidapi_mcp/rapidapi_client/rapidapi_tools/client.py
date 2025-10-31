"""Utilities for interacting with RapidAPI endpoints."""

import os
from typing import Any, Mapping
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import core_schema

__all__ = ["RapidAPIClient", "MissingRapidAPIKeyError", "clean_dict", "bool_to_str"]

load_dotenv()

class MissingRapidAPIKeyError(RuntimeError):
    """Raised when the RAPIDAPI_KEY environment variable has not been configured."""


def get_api_key(explicit_key: str | None = None) -> str:
    """Return the RapidAPI key, prioritising ``explicit_key`` then ``RAPIDAPI_KEY``.

    Args:
        explicit_key: Optional key passed directly to the client.

    Returns:
        The API key string.

    Raises:
        MissingRapidAPIKeyError: If the key cannot be located.
    """

    key = explicit_key or os.getenv("RAPIDAPI_KEY")
    if not key:
        raise MissingRapidAPIKeyError(
            "Set the RAPIDAPI_KEY environment variable or provide an explicit key "
            "when constructing RapidAPIClient."
        )
    return key


def clean_dict(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return a dictionary with ``None`` values removed."""

    return {key: value for key, value in data.items() if value is not None}


def bool_to_str(value: bool | None) -> str | None:
    """Convert a boolean value to the lowercase string expected by RapidAPI."""

    if value is None:
        return None
    return "true" if value else "false"


class RapidAPIClient:
    """Thin wrapper around :class:`httpx.AsyncClient` with RapidAPI defaults."""

    def __init__(self, api_key: str | None = None, *, timeout: float = 30.0) -> None:
        self.api_key = get_api_key(api_key)
        self.timeout = timeout

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: type[Any],
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        """Allow Pydantic to treat the client as an arbitrary type."""

        return core_schema.no_info_plain_validator_function(lambda value: value)

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema_: core_schema.CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> dict[str, Any]:
        """Provide a minimal JSON schema for documentation purposes."""

        return {"type": "object", "title": "RapidAPIClient"}

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Perform an HTTP request using the RapidAPI key."""

        parsed = urlparse(url)
        host_header = parsed.netloc
        request_headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": host_header,
        }
        if headers:
            request_headers.update(headers)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                url,
                params=params,
                json=json,
                headers=request_headers,
            )
            response.raise_for_status()
            return response.json()

    async def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Perform a GET request."""

        return await self.request("GET", url, params=params, headers=headers)

    async def post(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Perform a POST request."""

        return await self.request("POST", url, params=params, json=json, headers=headers)
