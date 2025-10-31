"""RapidAPI integrations for real estate tools."""

from typing import Any

from .client import RapidAPIClient, clean_dict


async def search_rental_properties(
    location: str,
    *,
    page: int = 1,
    sort_by: str = "relevance",
    price: dict[str, Any] | None = None,
    bedrooms: dict[str, Any] | None = None,
    min_bathrooms: int | None = None,
    home_types: list[str] | None = None,
    move_in_date: str | None = None,
    rental_amenities: list[str] | None = None,
    popular_filters: list[str] | None = None,
    home_size: dict[str, Any] | None = None,
    lot_size: dict[str, Any] | None = None,
    year_built: dict[str, Any] | None = None,
    basement_types: list[str] | None = None,
    amenities: list[str] | None = None,
    views: list[str] | None = None,
    time_on_zillow: dict[str, Any] | None = None,
    keywords: list[str] | None = None,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Search Zillow rental properties."""

    client = client or RapidAPIClient()
    body = clean_dict(
        {
            "location": location,
            "page": page,
            "sortBy": sort_by,
            "price": price,
            "bedrooms": bedrooms,
            "minBathrooms": min_bathrooms,
            "homeTypes": home_types,
            "moveInDate": move_in_date,
            "rentalAmenities": rental_amenities,
            "popularFilters": popular_filters,
            "homeSize": home_size,
            "lotSize": lot_size,
            "yearBuilt": year_built,
            "basementTypes": basement_types,
            "amenities": amenities,
            "views": views,
            "timeOnZillow": time_on_zillow,
            "keywords": keywords,
        }
    )
    data = await client.post(
        "https://zillow-com4.p.rapidapi.com/v2/properties/search-for-rent",
        json=body,
        headers={"Content-Type": "application/json"},
    )
    properties = data.get("props") or data.get("results") or data
    count = 0
    if isinstance(properties, list):
        count = len(properties)
    return {
        "location": location,
        "page": page,
        "sort_by": sort_by,
        "properties": properties,
        "count": count,
        "total_results": data.get("totalResultCount") or data.get("totalCount"),
    }


async def get_property_details(
    zpid: str,
    *,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Fetch detail information for a Zillow property."""

    client = client or RapidAPIClient()
    data = await client.get(
        "https://zillow-com4.p.rapidapi.com/v2/properties/detail",
        params={"zpid": zpid},
    )
    return {"zpid": zpid, "property": data.get("data", data)}
