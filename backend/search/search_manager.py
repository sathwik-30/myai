from backend.ai.model import (
    ask_ollama,
    answer_from_web
)

from backend.memory.manager import (
    MemoryManager
)

from backend.search.wikipedia import (
    search_wikipedia
)

from backend.search.web import (
    search_web
)


class SearchManager:

    def __init__(self):
        self.memory = MemoryManager()

    def process(self, question, context=""):

        # ------------------------------------------------
        # 1. CHECK MEMORY
        # ------------------------------------------------

        memory = self.memory.search(
            question
        )

        if memory:

            answer = ask_ollama(
                question,
                memory["answer"]
            )

            if answer:
                return {
                    "answer": answer,
                    "source": "memory"
                }

            return {
                "answer": memory["answer"],
                "source": "memory"
            }

        # ------------------------------------------------
        # 2. ASK OLLAMA
        # ------------------------------------------------

        answer = ask_ollama(
            question,
            context
        )

        if answer:

            return {
                "answer": answer,
                "source": "ollama"
            }

        # ------------------------------------------------
        # 3. SEARCH WIKIPEDIA
        # ------------------------------------------------

        wikipedia_results = search_wikipedia(
            question
        )

        if wikipedia_results:

            information = self._format_wikipedia(
                wikipedia_results
            )

            answer = answer_from_web(
                question,
                information
            )

            if answer:

                self.memory.learn(
                    question,
                    answer,
                    "wikipedia"
                )

                return {
                    "answer": answer,
                    "source": "wikipedia"
                }

        # ------------------------------------------------
        # 4. SEARCH INTERNET
        # ------------------------------------------------

        web_results = search_web(
            question
        )

        if web_results:

            information = self._format_web(
                web_results
            )

            answer = answer_from_web(
                question,
                information
            )

            if answer:

                self.memory.learn(
                    question,
                    answer,
                    "web"
                )

                return {
                    "answer": answer,
                    "source": "web"
                }

        # ------------------------------------------------
        # 5. NOTHING FOUND
        # ------------------------------------------------

        return {
            "answer": (
                "I couldn't find reliable information "
                "about that."
            ),
            "source": "unknown"
        }

    def _format_wikipedia(self, results):

        text_parts = []

        for item in results[:3]:

            title = item.get(
                "title",
                ""
            )

            snippet = item.get(
                "snippet",
                ""
            )

            text_parts.append(
                f"Title: {title}\n"
                f"Information: {snippet}"
            )

        return "\n\n".join(
            text_parts
        )

    def _format_web(self, results):

        text_parts = []

        for item in results[:5]:

            title = item.get(
                "title",
                ""
            )

            snippet = item.get(
                "snippet",
                ""
            )

            url = item.get(
                "url",
                ""
            )

            text_parts.append(
                f"Title: {title}\n"
                f"Information: {snippet}\n"
                f"Source: {url}"
            )

        return "\n\n".join(
            text_parts
        )