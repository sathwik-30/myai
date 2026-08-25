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

    def process(self, question, context=None):
        """
        Main Medha intelligence pipeline.

        Order:

        1. Persistent memory
        2. Ollama
        3. Wikipedia
        4. Internet
        5. Ollama synthesizes external information
        6. Save learned information
        """

        if context is None:
            context = []

        # ============================================
        # 1. CHECK PERSISTENT MEMORY
        # ============================================

        try:
            memory = self.memory.search(question)

        except Exception as error:
            print(
                f"[Memory] Search failed: {error}"
            )
            memory = None

        if memory:

            memory_answer = memory.get(
                "answer",
                ""
            )

            if memory_answer:

                ollama_result = ask_ollama(
                    question,
                    memory_answer
                )

                if (
                    ollama_result
                    and ollama_result.get("status")
                    == "answered"
                ):
                    return {
                        "answer": ollama_result["answer"],
                        "source": "memory"
                    }

                # Memory itself is still useful
                return {
                    "answer": memory_answer,
                    "source": "memory"
                }

        # ============================================
        # 2. ASK OLLAMA
        # ============================================

        try:
            ollama_result = ask_ollama(
                question,
                context
            )

        except Exception as error:
            print(
                f"[Ollama] Unexpected error: {error}"
            )

            ollama_result = {
                "status": "error",
                "answer": None,
                "error": str(error)
            }

        ollama_status = ollama_result.get(
            "status"
        )

        # ============================================
        # OLLAMA KNOWS
        # ============================================

        if ollama_status == "answered":

            return {
                "answer": ollama_result["answer"],
                "source": "ollama"
            }

        # ============================================
        # OLLAMA REFUSES
        # ============================================

        if ollama_status == "refused":

            refusal = ollama_result.get(
                "answer"
            )

            if refusal:

                return {
                    "answer": refusal,
                    "source": "ollama"
                }

        # ============================================
        # OLLAMA UNKNOWN / ERROR / OFFLINE
        # Continue to external sources
        # ============================================

        print(
            f"[Medha] Ollama status: "
            f"{ollama_status}"
        )

        # ============================================
        # 3. SEARCH WIKIPEDIA
        # ============================================

        wikipedia_results = []

        try:
            wikipedia_results = search_wikipedia(
                question
            )

        except Exception as error:
            print(
                f"[Wikipedia] Search failed: {error}"
            )

        if wikipedia_results:

            wikipedia_information = (
                self._format_wikipedia(
                    wikipedia_results
                )
            )

            ollama_result = answer_from_web(
                question,
                wikipedia_information
            )

            if (
                ollama_result
                and ollama_result.get("status")
                == "answered"
            ):

                answer = ollama_result["answer"]

                self._learn(
                    question,
                    answer,
                    "wikipedia"
                )

                return {
                    "answer": answer,
                    "source": "wikipedia"
                }

        # ============================================
        # 4. SEARCH INTERNET
        # ============================================

        web_results = []

        try:
            web_results = search_web(
                question
            )

        except Exception as error:
            print(
                f"[Web] Search failed: {error}"
            )

        if web_results:

            web_information = (
                self._format_web(
                    web_results
                )
            )

            ollama_result = answer_from_web(
                question,
                web_information
            )

            if (
                ollama_result
                and ollama_result.get("status")
                == "answered"
            ):

                answer = ollama_result["answer"]

                self._learn(
                    question,
                    answer,
                    "web"
                )

                return {
                    "answer": answer,
                    "source": "web"
                }

        # ============================================
        # 5. NOTHING RELIABLE FOUND
        # ============================================

        return {
            "answer": (
                "I couldn't find reliable information "
                "to answer that."
            ),
            "source": "unknown"
        }

    # ================================================
    # LEARNING
    # ================================================

    def _learn(
        self,
        question,
        answer,
        source
    ):

        try:

            self.memory.learn(
                question,
                answer,
                source
            )

            print(
                f"[Medha] Learned from {source}: "
                f"{question}"
            )

        except Exception as error:

            print(
                f"[Memory] Failed to save knowledge: "
                f"{error}"
            )

    # ================================================
    # WIKIPEDIA FORMATTER
    # ================================================

    def _format_wikipedia(
        self,
        results
    ):

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

    # ================================================
    # WEB FORMATTER
    # ================================================

    def _format_web(
        self,
        results
    ):

        text_parts = []

        for item in results[:8]:

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