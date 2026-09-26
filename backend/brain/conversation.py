from backend.brain.context import ConversationContext
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
        result = generate_response(
            message,
            self.context.get_messages(),
            self.knowledge,
            self.search_manager,
        )

        if isinstance(result, dict):
            response = result.get("answer", "")
            source = result.get("source", "memory")
        else:
            response = str(result)
            source = "memory"

        try:
            self.memory.learn_conversation(message, response)
        except Exception as error:
            print(f"[Memory] Conversation learning failed: {error}")

        self.context.add("user", message)
        self.context.add("assistant", response)

        return {
            "response": response,
            "source": source,
        }

    def history(self):
        return self.context.get_messages()
