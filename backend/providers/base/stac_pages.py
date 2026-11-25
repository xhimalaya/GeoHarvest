from urllib.parse import urljoin, urlsplit

import httpx


async def search_pages(client: httpx.AsyncClient, url: str, payload: dict, headers: dict) -> list[dict]:
    """Follow a STAC ItemCollection's GET or POST continuations up to the requested limit."""
    limit = payload["limit"]
    initial_body = {**payload, "limit": min(limit, 100)}
    origin = urlsplit(url)
    method, body = "POST", initial_body
    seen_requests = set()
    features = {}
    while True:
        request_key = (method, url, repr(body))
        if request_key in seen_requests:
            raise ValueError("Catalogue returned a repeated pagination link")
        seen_requests.add(request_key)
        response = await client.request(method, url, json=body, headers=headers)
        response.raise_for_status()
        page = response.json()
        for feature in page["features"]:
            features.setdefault(feature["id"], feature)
            if len(features) == limit:
                return list(features.values())
        link = next((link for link in page.get("links", []) if link.get("rel") == "next"), None)
        if not link:
            return list(features.values())
        url = urljoin(str(response.url), link["href"])
        target = urlsplit(url)
        if (target.scheme, target.netloc) != (origin.scheme, origin.netloc):
            raise ValueError("Catalogue returned a pagination link on a different origin")
        method = link.get("method", "GET").upper()
        if method not in {"GET", "POST"}:
            raise ValueError("Unsupported catalogue pagination method")
        body = None
        if method == "POST":
            body = link.get("body", {})
            if link.get("merge"):
                body = {**initial_body, **body}
