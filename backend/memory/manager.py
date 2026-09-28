from backend.memory.layers import (
    KNOWLEDGE,
    PERMANENT,
    PERSONAL,
    TEMPORARY,
    remember,
    search,
    search_all,
)


class MemoryManager:
    """Facade over Medha's four explicit memory layers."""

    def __init__(self, user_id=None):
        self.user_id = user_id

    def search(self, question, memory_scope=None):
        if memory_scope:
            results = search(memory_scope, self.user_id, question, top_k=1, min_score=0.40)
        else:
            results = search_all(self.user_id, question, top_k=1)
        return results[0] if results else None

    def learn(
        self,
        question,
        answer,
        source,
        importance=3,
        memory_type=KNOWLEDGE,
        memory_scope=None,
        expires_at=None,
    ):
        if not question or not answer:
            return False

        scope = memory_scope
        if scope is None:
            scope = {
                PERSONAL: PERSONAL,
                TEMPORARY: TEMPORARY,
                PERMANENT: PERMANENT,
                KNOWLEDGE: KNOWLEDGE,
            }.get(memory_type, KNOWLEDGE)

        return remember(
            scope=scope,
            user_id=self.user_id,
            text=question,
            answer=answer,
            source=source,
            importance=importance,
            expires_at=expires_at,
        )

    def learn_personal(self, fact, answer, importance=5):
        return self.learn(
            fact,
            answer,
            source="user",
            importance=importance,
            memory_type=PERSONAL,
            memory_scope=PERSONAL,
        )

    def learn_permanent(self, fact, answer, source="user", importance=5):
        """Store something the owner explicitly taught Medha to retain permanently."""
        return self.learn(
            fact,
            answer,
            source=source,
            importance=importance,
            memory_type=PERMANENT,
            memory_scope=PERMANENT,
        )

    def learn_knowledge(self, question, answer, source="web", importance=4):
        """Store learned external knowledge with six-month inactivity expiry."""
        return self.learn(
            question,
            answer,
            source=source,
            importance=importance,
            memory_type=KNOWLEDGE,
            memory_scope=KNOWLEDGE,
        )

    def learn_temporary(self, question, answer, source="temporary_resource", importance=3, expires_at=None):
        return self.learn(
            question,
            answer,
            source=source,
            importance=importance,
            memory_type=TEMPORARY,
            memory_scope=TEMPORARY,
            expires_at=expires_at,
        )

    def search_personal(self, question):
        return self.search(question, memory_scope=PERSONAL)

    def search_permanent(self, question):
        return self.search(question, memory_scope=PERMANENT)

    def search_knowledge(self, question):
        return self.search(question, memory_scope=KNOWLEDGE)

    def search_temporary(self, question):
        return self.search(question, memory_scope=TEMPORARY)

    def counts(self):
        from backend.memory.layers import counts
        return counts(self.user_id)

    def learn_conversation(self, user_message, assistant_answer):
        return self.learn_temporary(user_message, assistant_answer)
