"""Public web search for Medha, returning usable source URLs."""
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

USER_AGENT = "MedhaPersonalAssistant/1.0"
TIMEOUT = (3.0, 7.0)


def search_web(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Return search results with titles, snippets, and destination URLs."""
    query = " ".join(str(query or "").split())[:500]
    if not query:
        return []
    try:
        response = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for result in soup.select(".result"):
            anchor = result.select_one(".result__title a")
            if not anchor:
                continue
            href = str(anchor.get("href", "")).strip()
            if href.startswith("//"):
                href = "https:" + href
            parsed = urlparse(href)
            if "duckduckgo.com" in (parsed.hostname or "") and parsed.path.startswith("/l/"):
                href = parse_qs(parsed.query).get("uddg", [href])[0]
            if urlparse(href).scheme not in {"http", "https"}:
                continue
            snippet = result.select_one(".result__snippet")
            results.append({
                "title": anchor.get_text(" ", strip=True)[:300],
                "snippet": snippet.get_text(" ", strip=True)[:1200] if snippet else "",
                "url": href,
            })
            if len(results) >= max(1, min(int(limit), 10)):
                break
        return results
    except (requests.RequestException, ValueError, TypeError):
        return []
