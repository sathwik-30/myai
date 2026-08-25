import requests

def search_wikipedia(query):
    url="https://en.wikipedia.org/w/api.php"

    params={
        "action":"query",
        "list":"search",
        "srsearch":query,
        "format":"json",
        "utf8":1,
        "srlimit":3
    }

    try:
        response=requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data=response.json()

        results=data.get("query",{}).get("search",[])

        if not results:
            return None

        return results

    except requests.RequestException:
        return None