import requests
from bs4 import BeautifulSoup


def search_web(query):
    try:
        response = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Medha/1.0 personal-assistant"},
            timeout=5,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for result in soup.select(".result")[:3]:
            title_element = result.select_one(".result__title")
            if not title_element:
                continue

            snippet_element = result.select_one(".result__snippet")
            link_element = result.select_one(".result__url")

            results.append({
                "title": title_element.get_text(" ", strip=True),
                "snippet": snippet_element.get_text(" ", strip=True) if snippet_element else "",
                "url": link_element.get_text(" ", strip=True) if link_element else "",
            })

        return results
    except (requests.RequestException, ValueError, TypeError):
        return []
