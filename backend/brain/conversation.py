from backend.brain.context import ConversationContext
from backend.brain.intent import classify
from backend.brain.response import generate_response
from backend.knowledge.knowledge_base import KnowledgeBase
from backend.search.search_manager import SearchManager
from backend.memory.evaluator import evaluate_memory
from backend.memory.manager import MemoryManager


class ConversationEngine:
    def __init__(self):
        self.context = ConversationContext()
        self.knowledge = KnowledgeBase()
        self.search_manager = SearchManager()
        self.memory = MemoryManager()

    def chat(self, message):
        history = self.context.get_messages()
        result = generate_response(
            message,
            history,
            self.knowledge,
            self.search_manager,
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

        # Automatically preserve information that is likely to matter later.
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

        self.context.add("user", message)
        self.context.add("assistant", response)

        return {
            "response": response,
            "source": source,
        }

    def history(self):
        return self.context.get_messages()
