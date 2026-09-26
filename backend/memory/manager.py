from backend.memory.knowledge_store import search_memory
from backend.memory.semantic_memory import search as semantic_search
from backend.memory.semantic_memory import remember


class MemoryManager:
    def __init__(self, user_id=None):
        self.user_id = user_id

    def search(self, question):
        semantic_results = semantic_search(
            question,
            top_k=1,
            min_score=0.40,
            user_id=self.user_id,
        )
        if semantic_results:
            return semantic_results[0]
        # Legacy knowledge store is global and is retained only as a
        # compatibility fallback for old non-personal data.
        return search_memory(question)

    def learn(
        self,
        question,
        answer,
        source,
        importance=3,
        memory_type="knowledge",
    ):
        if not question or not answer:
            return False

        remember(
            question,
            answer,
            memory_type=memory_type,
            source=source,
            metadata={"importance": importance},
            importance=importance,
            user_id=self.user_id,
        )
        return True

    def learn_personal(self, fact, answer, importance=5):
        return self.learn(
            fact,
            answer,
            source="user",
            importance=importance,
            memory_type="personal",
        )

    def learn_conversation(self, user_message, assistant_answer):
        return False
