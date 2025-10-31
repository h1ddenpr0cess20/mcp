"""RapidAPI integrations for job search tools."""

from typing import Any

from .client import RapidAPIClient, bool_to_str, clean_dict


async def search_jobs(
    query: str,
    *,
    page: int = 1,
    num_pages: int = 1,
    country: str = "us",
    date_posted: str = "all",
    work_from_home: bool | None = None,
    employment_types: str | None = None,
    job_requirements: str | None = None,
    radius: int | None = None,
    exclude_job_publishers: str | None = None,
    fields: str | None = None,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Search job listings using the JSearch API."""

    client = client or RapidAPIClient()
    params = clean_dict(
        {
            "query": query,
            "page": page,
            "num_pages": num_pages,
            "country": country,
            "date_posted": date_posted,
            "work_from_home": bool_to_str(work_from_home),
            "employment_types": employment_types,
            "job_requirements": job_requirements,
            "radius": radius,
            "exclude_job_publishers": exclude_job_publishers,
            "fields": fields,
        }
    )
    data = await client.get("https://jsearch.p.rapidapi.com/search", params=params)
    return {
        "query": query,
        "page": page,
        "results": data.get("data", []),
        "count": len(data.get("data", []) or []),
        "status": data.get("status"),
        "request_id": data.get("request_id"),
        "parameters": data.get("parameters"),
    }


async def get_job_details(
    job_id: str,
    *,
    country: str = "us",
    language: str | None = None,
    fields: str | None = None,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Fetch detailed information about a specific job posting."""

    client = client or RapidAPIClient()
    params = clean_dict(
        {
            "job_id": job_id,
            "country": country,
            "language": language,
            "fields": fields,
        }
    )
    data = await client.get("https://jsearch.p.rapidapi.com/job-details", params=params)
    return {
        "job_id": job_id,
        "data": data.get("data", data),
        "status": data.get("status"),
        "request_id": data.get("request_id"),
        "parameters": data.get("parameters"),
    }
