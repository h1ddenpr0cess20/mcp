import asyncio

from rapidapi_client.rapidapi_tools.search import (
    get_business_details,
    get_business_reviews,
    local_business_search,
    search_web,
)


class StubRapidAPIClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def get(self, url, *, params=None, headers=None):
        self.calls.append({"url": url, "params": params})
        return self.payload


def test_search_web_passes_query():
    payload = {"data": [{"title": "Result"}]}
    client = StubRapidAPIClient(payload)

    result = asyncio.run(search_web("how to build a website", client=client))

    call = client.calls[0]
    assert call["url"] == "https://real-time-web-search.p.rapidapi.com/search-light"
    assert call["params"] == {"q": "how to build a website"}
    assert result["count"] == 1
    assert result["results"][0]["title"] == "Result"


def test_local_business_search_limits_and_flags():
    payload = {"data": [{"name": "Coffee Shop"}]}
    client = StubRapidAPIClient(payload)

    result = asyncio.run(
        local_business_search(
            "coffee",
            limit=100,
            lat=43.65,
            lng=-79.38,
            zoom=14,
            language="en",
            region="ca",
            extract_emails_and_contacts=True,
            subtypes="cafe",
            verified=True,
            business_status="OPERATIONAL",
            fields="name,place_id",
            client=client,
        )
    )

    call = client.calls[0]
    params = call["params"]
    assert params["limit"] == 50  # capped value
    assert params["extract_emails_and_contacts"] == "true"
    assert params["verified"] == "true"
    assert params["subtypes"] == "cafe"
    assert params["business_status"] == "OPERATIONAL"
    assert params["fields"] == "name,place_id"
    assert result["count"] == 1
    assert result["businesses"][0]["name"] == "Coffee Shop"


def test_get_business_details_converts_boolean_flags():
    payload = {"data": {"name": "Bakery"}}
    client = StubRapidAPIClient(payload)

    result = asyncio.run(
        get_business_details(
            "place-id",
            extract_emails_and_contacts=True,
            extract_share_link=False,
            fields="name,rating",
            region="us",
            language="en",
            client=client,
        )
    )

    call = client.calls[0]
    params = call["params"]
    assert params["business_id"] == "place-id"
    assert params["extract_emails_and_contacts"] == "true"
    assert params["extract_share_link"] == "false"
    assert params["fields"] == "name,rating"
    assert params["region"] == "us"
    assert params["language"] == "en"
    assert result["business"]["name"] == "Bakery"


def test_get_business_reviews_handles_optional_parameters():
    payload = {"data": [{"rating": 5}]}
    client = StubRapidAPIClient(payload)

    result = asyncio.run(
        get_business_reviews(
            "place-id",
            limit=10,
            offset=5,
            translate_reviews=True,
            query="croissant",
            sort_by="rating",
            fields="rating,text",
            region="us",
            client=client,
        )
    )

    call = client.calls[0]
    params = call["params"]
    assert params["business_id"] == "place-id"
    assert params["limit"] == 10
    assert params["offset"] == 5
    assert params["translate_reviews"] == "true"
    assert params["query"] == "croissant"
    assert params["sort_by"] == "rating"
    assert params["fields"] == "rating,text"
    assert params["region"] == "us"
    assert result["count"] == 1
    assert result["reviews"][0]["rating"] == 5
