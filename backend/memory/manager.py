from backend.memory.knowledge_store import search_memory
from backend.memory.semantic_memory import search as semantic_search
from backend.memory.semantic_memory import remember


class MemoryManager:
    def search(self, question):
        semantic_results = semantic_search(question, top_k=1, min_score=0.45)
        if semantic_results:
            return semantic_results[0]
        return search_memory(question)

    def learn(self, question, answer, source, importance=3, memory_type="knowledge"):
        if not question or not answer:
            return False

        remember(
            question,
            answer,
            memory_type=memory_type,
            source=source,
            metadata={"importance": importance},
        )
        return True

    def learn_conversation(self, user_message, assistant_answer):
        return self.learn(
            user_message,
            assistant_answer,
            source="conversation",
            memory_type="conversation",
        )
