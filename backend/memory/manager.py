from backend.memory.knowledge_store import (
    search_memory,
    save_knowledge
)


class MemoryManager:

    def search(self, question):
        return search_memory(question)

    def learn(self, question, answer, source):
        save_knowledge(
            question,
            answer,
            source
        )