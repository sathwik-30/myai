from backend.brain.context import ConversationContext
from backend.brain.intent import classify
from backend.brain.response import generate_response
from backend.knowledge.knowledge_base import KnowledgeBase
from backend.search.search_manager import SearchManager
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

        # If Medha asked the user to supply an unknown casual fact,
        # treat the next user message as the answer to the previous question.
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

        # Explicit memory statements should be stored as personal knowledge.
        elif classify(message) == "memory":
            self.memory.learn_personal(
                message,
                message,
                importance=5,
            )
            response = "Got it. I'll remember that."
            source = "memory_saved"

        self.context.add("user", message)
        self.context.add("assistant", response)

        return {
            "response": response,
            "source": source,
        }

    def history(self):
        return self.context.get_messages()
