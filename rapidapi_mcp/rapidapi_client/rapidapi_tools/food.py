"""RapidAPI integrations for food and recipe tools."""

from typing import Any

from .client import RapidAPIClient, clean_dict


async def search_recipes(
    query: str,
    *,
    offset: int = 0,
    size: int = 10,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Search the Tasty API for recipes."""

    client = client or RapidAPIClient()
    size = min(size, 40)
    params = clean_dict(
        {
            "q": query,
            "from": offset,
            "size": size,
        }
    )
    data = await client.get("https://tasty.p.rapidapi.com/recipes/list", params=params)
    recipes = data.get("results", []) or []
    processed: list[dict[str, Any]] = []
    for recipe in recipes:
        processed.append(
            {
                "id": recipe.get("id"),
                "name": recipe.get("name"),
                "description": recipe.get("description"),
                "thumbnail_url": recipe.get("thumbnail_url"),
                "video_url": recipe.get("video_url"),
                "cook_time_minutes": recipe.get("cook_time_minutes"),
                "prep_time_minutes": recipe.get("prep_time_minutes"),
                "total_time_minutes": recipe.get("total_time_minutes"),
                "servings": recipe.get("num_servings"),
                "difficulty": recipe.get("difficulty"),
                "tags": [tag.get("name") for tag in recipe.get("tags", []) if tag.get("name")],
                "nutrition": recipe.get("nutrition"),
                "instructions": [
                    step.get("display_text")
                    for step in recipe.get("instructions", [])
                    if step.get("display_text")
                ],
                "ingredients": [
                    component.get("raw_text")
                    for section in recipe.get("sections", [])
                    for component in section.get("components", [])
                    if component.get("raw_text")
                ],
            }
        )

    return {
        "query": query,
        "offset": offset,
        "size": size,
        "count": len(processed),
        "total_count": data.get("count", len(processed)),
        "recipes": processed,
    }
