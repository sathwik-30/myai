from backend.brain.identity import OWNER_NAME
from backend.brain.intent import classify, understand
from backend.brain.understanding import LanguageUnderstanding
from backend.brain.language import detect_language
from backend.core.policy import apply_override
from backend.memory.layers import search_all

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
    lines.append("If the question is ambiguous, give me one extra detail and I can narrow the meaning.")
    return "\n".join(lines)


def _local_answer(intent: str, message: str, user_id=None):
    if intent == "greeting":
        return f"Hello {OWNER_NAME}. I'm Medha, ready to help.", "local_brain"
    if intent == "status":
        return "I'm running locally and ready to process your request.", "local_brain"
    if intent == "identity":
        return "I'm Medha, your independent personal AI assistant.", "local_brain"
    if intent == "capability":
        return (
            "I can understand learned language patterns, use persistent memory, "
            "search connected knowledge, and work with local tools. My runtime "
            "does not require Ollama or another LLM.",
            "local_brain",
        )
    if intent == "thanks":
        return "You're welcome.", "local_brain"
    if intent == "personal":
        return "Got it. I'll keep that in mind for future conversations.", "personal"
    if intent == "memory":
        return "Tell me the information you want me to remember, and I'll store the useful part.", "memory_request"
    return None


def generate_response(message, context, knowledge, search_manager, user_id=None):
    message = str(message or "").strip()

    policy_check = apply_override("", message)
    if not policy_check["allowed"]:
        return {"answer": policy_check["response"], "source": "core_override"}

    if not message:
        return {"answer": f"I'm here, {OWNER_NAME}. Say something.", "source": "system"}

    # Memory is checked before general knowledge so user corrections/preferences
    # can influence the conversation without changing model weights.
    answer = UNDERSTANDING.best_memory_answer(message, context, user_id)
    if answer:
        return {"answer": answer, "source": "memory"}

    parsed = understand(message)
    intent = parsed["intent"]

    local = _local_answer(intent, message, user_id)
    if local:
        return {"answer": local[0], "source": local[1], "intent": intent, "confidence": parsed["confidence"]}

    # Technical, knowledge, research, and unknown questions use Medha's local
    # retrieval/search layer. No external LLM is called to formulate an answer.
    result = search_manager.process(message, context)
    if result and result.get("answer"):
        return {
            "answer": result["answer"],
            "source": result.get("source", "search"),
            "intent": intent,
            "confidence": parsed["confidence"],
        }

    if result and result.get("source") == "knowledge_gap":
        return {
            "answer": _format_knowledge_gap(result, message),
            "source": "knowledge_gap",
            "intent": intent,
            "confidence": parsed["confidence"],
        }

    return {
        "answer": f"I couldn't find reliable information about that yet, {OWNER_NAME}.",
        "source": "fallback",
        "intent": intent,
        "confidence": parsed["confidence"],
    }
