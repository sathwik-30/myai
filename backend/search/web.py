import requests
from bs4 import BeautifulSoup


def search_web(query):
    url = "https://html.duckduckgo.com/html/"

    try:
        response = requests.get(
            url,
            params={
                "q": query
            },
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=15
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        results = []

        for result in soup.select(
            ".result"
        )[:5]:

            title_element = result.select_one(
                ".result__title"
            )

            snippet_element = result.select_one(
                ".result__snippet"
            )

            link_element = result.select_one(
                ".result__url"
            )

            if not title_element:
                continue

            title = title_element.get_text(
                " ",
                strip=True
            )

            snippet = ""

            if snippet_element:
                snippet = snippet_element.get_text(
                    " ",
                    strip=True
                )

            link = ""

            if link_element:
                link = link_element.get_text(
                    " ",
                    strip=True
                )

            results.append({
                "title": title,
                "snippet": snippet,
                "url": link
            })

        return results

    except requests.RequestException:
        return []

    except Exception:
        return []