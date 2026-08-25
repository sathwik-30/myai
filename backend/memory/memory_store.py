from backend.memory.knowledge_store import (
    search_memory,
    save_knowledge
)


def get_memory(question):
    return search_memory(question)


def store_memory(question, answer, source):
    save_knowledge(
        question,
        answer,
        source
    )