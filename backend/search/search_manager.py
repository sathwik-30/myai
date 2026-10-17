from backend.memory.manager import MemoryManager
from backend.search.wikipedia import search_wikipedia
from backend.search.web import search_web
from backend.knowledge.resource_loader import search_resources


class SearchManager:
    """Retrieve learned knowledge first, then local resources and public sources."""

    def __init__(self, user_id=None):
        self.memory = MemoryManager(user_id=user_id)

    def process(self, question, context=None):
        # Reuse knowledge learned from earlier research or explicitly taught by
        # the owner. This is what lets paraphrased questions benefit from memory.
        try:
            learned = self.memory.search_knowledge(question)
            if learned and float(learned.get("score", 0.0)) >= 0.55:
                return {
                    "answer": learned.get("answer"),
                    "source": "learned_knowledge",
                }
        except Exception:
            pass

        local_results = search_resources(question)
        if local_results:
            item = local_results[0]
            return {
                "answer": item["text"],
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
        self.memory.learn_knowledge(question, answer, source=source, importance=4)

    @staticmethod
    def _best_wikipedia_answer(results):
        item = results[0]
        answer = item.get("extract") or item.get("snippet") or item.get("title")
        url = item.get("url")
        if answer and url:
            return f"{answer}\nSource: {url}"
        return answer

    @staticmethod
    def _best_web_answer(results):
        item = results[0]
        title = item.get("title") or "Web result"
        snippet = item.get("snippet") or ""
        url = item.get("url") or ""
        parts = [title, snippet]
        if url:
            parts.append(f"Source: {url}")
        return "\n".join(part for part in parts if part)
