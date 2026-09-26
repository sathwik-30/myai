import logging

from backend.brain.context import ConversationContext
from backend.brain.intent import classify
from backend.brain.response import generate_response
from backend.search.search_manager import SearchManager
from backend.memory.evaluator import evaluate_memory
from backend.memory.manager import MemoryManager


logger = logging.getLogger("medha.conversation")


class ConversationEngine:
    """
    Local conversation engine.

    Knowledge/search services are created lazily so a failure in an optional
    knowledge component cannot prevent simple local-memory responses.
    """

    def __init__(self, user_id=None):
        self.user_id = user_id
        self.context = ConversationContext()
        self.search_manager = None
        self.memory = MemoryManager(user_id=user_id)

    def _get_search_manager(self):
        if self.search_manager is None:
            self.search_manager = SearchManager(user_id=self.user_id)
        return self.search_manager

    @staticmethod
    def _safe_local_response(message):
        text = " ".join(str(message or "").lower().split())

        if text in {"hi", "hello", "hey", "hey medha"}:
            return "Hey Sathwik. I'm here.", "memory"

        if text in {"thanks", "thank you"}:
            return "You're welcome.", "memory"

        if text in {"how are you", "how are you?"}:
            return "I'm functioning normally and ready to talk with you.", "memory"

        return (
            "I hit a temporary problem while processing that. Your message is saved, "
            "so you can retry it without losing the conversation.",
            "fallback",
        )

    def chat(self, message):
        history = self.context.get_messages()

        try:
            result = generate_response(
                message,
                history,
                None,
                self._get_search_manager(),
                self.user_id,
            )

            if isinstance(result, dict):
                response = result.get("answer", "")
                source = result.get("source", "memory")
            else:
                response = str(result)
                source = "memory"

            # Answer an unknown casual/personal fact when the previous turn
            # explicitly asked the user to supply it.
            if history and history[-1].get("role") == "assistant":
                previous_answer = history[-1].get("message", "")
                if previous_answer.startswith("I don't know that yet.") and message.strip():
                    previous_question = ""
                    if len(history) >= 2 and history[-2].get("role") == "user":
                        previous_question = history[-2].get("message", "")

                    if previous_question:
                        self.memory.learn_personal(
                            previous_question,
                            message.strip(),
                            importance=5,
                        )
                        response = "Got it. I'll remember that for our future conversations."
                        source = "memory_saved"

            elif classify(message) in {"memory", "personal"}:
                self.memory.learn_personal(
                    message,
                    message,
                    importance=5 if classify(message) == "memory" else 4,
                )
                response = (
                    "Got it. I'll remember that."
                    if classify(message) == "memory"
                    else "Got it. I'll keep that in mind for future conversations."
                )
                source = "memory_saved"

            else:
                decision = evaluate_memory(message, response, source)
                if decision["save"] and source not in {"fallback", "ask_user", "memory_request"}:
                    self.memory.learn(
                        message,
                        response,
                        source=source,
                        importance=decision["importance"],
                        memory_type=decision["memory_type"],
                    )

        except Exception:
            logger.exception("Conversation generation failed; using local fallback")
            response, source = self._safe_local_response(message)

        self.context.add("user", message)
        self.context.add("assistant", response)

        return {
            "response": response,
            "source": source,
        }

    def history(self):
        return self.context.get_messages()
