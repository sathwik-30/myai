from backend.memory.manager import MemoryManager
from backend.search.wikipedia import search_wikipedia
from backend.search.web import search_web
from backend.knowledge.resource_loader import search_resources


class SearchManager:
    def __init__(self):
        self.memory = MemoryManager()

    def process(self, question, context=None):
        memory = self.memory.search(question)

        if memory:
            return {
                "answer": memory["answer"],
                "source": memory.get("source", "memory"),
            }

        local_results = search_resources(question)
        if local_results:
            item = local_results[0]
            answer = item["text"]
            return {
                "answer": answer,
                "source": "local_resource",
                "resource": item["path"],
            }

        wikipedia_results = search_wikipedia(question)
        if wikipedia_results:
            answer = self._best_wikipedia_answer(wikipedia_results)
            if answer:
                self._learn(question, answer, "wikipedia")
                return {"answer": answer, "source": "wikipedia"}

        web_results = search_web(question)
        if web_results:
            answer = self._best_web_answer(web_results)
            if answer:
                self._learn(question, answer, "web")
                return {"answer": answer, "source": "web"}

        return {"answer": None, "source": "unknown"}

    def _learn(self, question, answer, source):
        self.memory.learn(question, answer, source)

    @staticmethod
    def _best_wikipedia_answer(results):
        item = results[0]
        return item.get("extract") or item.get("snippet") or item.get("title")

    @staticmethod
    def _best_web_answer(results):
        item = results[0]
        return item.get("snippet") or item.get("title")
