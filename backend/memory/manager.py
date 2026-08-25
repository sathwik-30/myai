from datetime import datetime

from backend.memory.knowledge_store import (
    search_memory,
    save_knowledge
)


class MemoryManager:

    # -----------------------------------------
    # SEARCH
    # -----------------------------------------

    def search(self, question):
        return search_memory(question)

    # -----------------------------------------
    # SAVE
    # -----------------------------------------

    def learn(
        self,
        question,
        answer,
        source,
        importance=3,
        memory_type="knowledge"
    ):
        """
        Save useful information for future retrieval.

        importance:
            1 = low
            2 = useful
            3 = important
            4 = very important
            5 = critical / permanent
        """

        if not question or not answer:
            return False

        importance = max(
            1,
            min(5, int(importance))
        )

        save_knowledge(
            question,
            answer,
            source,
            importance=importance,
            memory_type=memory_type,
            created_at=datetime.utcnow().isoformat()
        )

        return True