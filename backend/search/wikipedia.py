import requests


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"


def search_wikipedia(query):
    """
    Search Wikipedia and retrieve useful article extracts.
    """

    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "utf8": 1,
        "srlimit": 5
    }

    try:
        response = requests.get(
            WIKIPEDIA_API,
            params=search_params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        search_results = (
            data
            .get("query", {})
            .get("search", [])
        )

        if not search_results:
            return []

        results = []

        for item in search_results:

            title = item.get(
                "title",
                ""
            )

            page_id = item.get(
                "pageid"
            )

            snippet = item.get(
                "snippet",
                ""
            )

            if not page_id:
                continue

            article_params = {
                "action": "query",
                "pageids": page_id,
                "prop": "extracts|info",
                "explaintext": 1,
                "exintro": 1,
                "inprop": "url",
                "format": "json",
                "utf8": 1
            }

            article_response = requests.get(
                WIKIPEDIA_API,
                params=article_params,
                timeout=10
            )

            article_response.raise_for_status()

            article_data = (
                article_response.json()
            )

            pages = (
                article_data
                .get("query", {})
                .get("pages", {})
            )

            page = pages.get(
                str(page_id),
                {}
            )

            extract = page.get(
                "extract",
                ""
            )

            url = page.get(
                "fullurl",
                f"https://en.wikipedia.org/wiki/"
                f"{title.replace(' ', '_')}"
            )

            results.append({
                "title": title,
                "snippet": snippet,
                "extract": extract,
                "url": url
            })

        return results

    except requests.RequestException as error:

        print(
            f"[Wikipedia] Request failed: {error}"
        )

        return []

    except Exception as error:

        print(
            f"[Wikipedia] Unexpected error: {error}"
        )

        return []