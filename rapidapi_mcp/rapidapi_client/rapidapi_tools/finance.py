"""RapidAPI integrations for finance-related tools."""

from typing import Any

from .client import RapidAPIClient, clean_dict


async def get_twelve_data_price(
    symbol: str,
    *,
    format: str = "json",
    outputsize: int = 30,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Fetch the latest price for a symbol from Twelve Data."""

    client = client or RapidAPIClient()
    params = clean_dict({
        "symbol": symbol.upper(),
        "format": format,
        "outputsize": outputsize,
    })
    data = await client.get("https://twelve-data1.p.rapidapi.com/price", params=params)
    return {"symbol": symbol.upper(), "data": data}


async def get_twelve_data_quote(
    symbol: str,
    *,
    interval: str,
    format: str = "json",
    outputsize: int = 30,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Fetch quote data for a symbol from Twelve Data."""

    client = client or RapidAPIClient()
    params = clean_dict(
        {
            "symbol": symbol.upper(),
            "interval": interval,
            "format": format,
            "outputsize": outputsize,
        }
    )
    data = await client.get("https://twelve-data1.p.rapidapi.com/quote", params=params)
    return {"symbol": symbol.upper(), "data": data}
