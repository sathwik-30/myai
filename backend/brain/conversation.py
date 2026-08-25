from backend.brain.context import ConversationContext
from backend.brain.response import generate_response
from backend.knowledge.knowledge_base import KnowledgeBase
from backend.search.search_manager import SearchManager

class ConversationEngine:
    def __init__(self):
        self.context=ConversationContext()
        self.knowledge=KnowledgeBase()
        self.search_manager=SearchManager()

    def chat(self,message):
        response=generate_response(
            message,
            self.context.get_messages(),
            self.knowledge,
            self.search_manager
        )

        self.context.add(
            "user",
            message
        )

        self.context.add(
            "assistant",
            response
        )

        return response