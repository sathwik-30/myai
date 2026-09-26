from backend.brain.identity import OWNER_NAME
from backend.brain.intent import classify
from backend.brain.understanding import LanguageUnderstanding
from backend.core.policy import apply_override

UNDERSTANDING = LanguageUnderstanding()


def _format_knowledge_gap(result, message):
    subject = result.get("understood_as") or "that topic"
    ideas = result.get("ideas") or []

    lines = [
        f"I don't have a reliable answer for '{subject}' yet.",
        f"I understand your question as being about {subject}.",
        "I don't want to invent a fact just to sound confident.",
    ]

    if ideas:
        lines.append("Useful directions to investigate:")
        lines.extend(f"- {idea}" for idea in ideas[:4])

    lines.append(
        "If the question is ambiguous, give me one extra detail and I can narrow the meaning."
    )
    return "\n".join(lines)


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

    if result and result.get("source") == "knowledge_gap":
        return {
            "answer": _format_knowledge_gap(result, message),
            "source": "knowledge_gap",
        }

    return {
        "answer": f"I couldn't find reliable information about that yet, {OWNER_NAME}.",
        "source": "fallback",
    }
