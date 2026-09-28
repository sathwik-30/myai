import requests


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
REQUEST_TIMEOUT = 3


def search_wikipedia(query):
    """Return one useful Wikipedia result without making a request per result."""

    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrlimit": 1,
        "prop": "extracts|info",
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
        "format": "json",
        "utf8": 1,
    }

    try:
        response = requests.get(
            WIKIPEDIA_API,
            params=params,
            headers={"User-Agent": "Medha/1.0 personal-assistant"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {})
        if not pages:
            return []

        page = next(iter(pages.values()))
        title = page.get("title", "")
        extract = page.get("extract", "").strip()
        url = page.get(
            "fullurl",
            f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
        )

        if not title and not extract:
            return []

        return [{
            "title": title,
            "snippet": extract[:500],
            "extract": extract,
            "url": url,
        }]
    except (requests.RequestException, ValueError, TypeError):
        return []
