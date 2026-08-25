from backend.search.wikipedia import search_wikipedia
from backend.search.web import search_web

class SearchManager:
    def search(self,query):
        wikipedia_results=search_wikipedia(query)

        if wikipedia_results:
            return {
                "source":"wikipedia",
                "results":wikipedia_results
            }

        web_results=search_web(query)

        if web_results:
            return {
                "source":"web",
                "results":web_results
            }

        return None