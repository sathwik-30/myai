from backend.brain.identity import OWNER_NAME
from backend.brain.intent import classify
from backend.brain.understanding import LanguageUnderstanding
from backend.memory.semantic_memory import remember
from backend.core.policy import apply_override

UNDERSTANDING = LanguageUnderstanding()


def generate_response(message, context, knowledge, search_manager):
    message = message.strip()

    policy_check = apply_override("", message)
    if not policy_check["allowed"]:
        return {
            "answer": policy_check["response"],
            "source": "core_override",
        }

    if not message:
        return {
            "answer": f"I'm here, {OWNER_NAME}. Say something.",
            "source": "system",
        }

    answer = UNDERSTANDING.best_memory_answer(message, context)
    if answer:
        return {
            "answer": answer,
            "source": "memory",
        }

    intent = classify(message)

    if intent in {"casual", "memory", "personal"}:
        if intent == "personal":
            return {
                "answer": "Got it. I'll keep that in mind for future conversations.",
                "source": "personal",
            }

        if intent == "memory":
            return {
                "answer": (
                    "I don't know that yet. Tell me the important detail and "
                    "I'll remember it for future conversations."
                ),
                "source": "memory_request",
            }

        return {
            "answer": (
                "I don't know that yet. Tell me the answer and I'll remember "
                "the useful part for future conversations."
            ),
            "source": "ask_user",
        }

    result = search_manager.process(message, context)

    if result and result.get("answer"):
        return {
            "answer": result["answer"],
            "source": result.get("source", "search"),
        }

    return {
        "answer": (
            f"I couldn't find reliable information about that yet, {OWNER_NAME}."
        ),
        "source": "fallback",
    }
