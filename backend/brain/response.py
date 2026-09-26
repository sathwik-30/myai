from backend.brain.identity import OWNER_NAME
from backend.brain.understanding import LanguageUnderstanding
from backend.memory.semantic_memory import remember

UNDERSTANDING = LanguageUnderstanding()

def generate_response(message, context, knowledge, search_manager):
    message = message.strip()

    if not message:
        return f"I'm here, {OWNER_NAME}. Say something."

    answer = UNDERSTANDING.best_memory_answer(message, context)
    if answer:
        return answer

    result = search_manager.process(message, context)

    if result and result.get("answer"):
        answer = result["answer"]
        remember(
            message,
            answer,
            memory_type="knowledge",
            source=result.get("source", "search"),
        )
        return answer

    return (
        f"I don't have enough learned information to answer that yet, "
        f"{OWNER_NAME}."
    )
