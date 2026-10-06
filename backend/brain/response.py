from backend.brain.identity import OWNER_NAME
from backend.brain.intent import understand
from backend.brain.understanding import LanguageUnderstanding
from backend.core.policy import apply_override

UNDERSTANDING = LanguageUnderstanding()

_CONVERSATIONAL_INTENTS = {
    "greeting", "status", "identity", "capability", "thanks", "memory",
    "personal", "technical", "knowledge", "research", "general", "casual",
    "permanent",
}


def _local_answer(intent: str, message: str, context=None):
    text = " ".join(str(message or "").lower().split())

    # Deterministic conversational responses must not depend on the optional
    # local decoder. These are core assistant behaviors.
    if text in {"hi", "hello", "hey", "hey medha", "hi medha", "hello medha"}:
        return f"Hi {OWNER_NAME}. I'm here. How are you?", "local_brain"

    if text in {"how are you", "how are you?", "how r u", "how r u?"}:
        return "I'm doing well, Sathwik. I'm running locally and ready to talk.", "local_brain"

    if text in {"so", "then", "and then"}:
        return "I'm here. Tell me what you want to do next.", "local_brain"

    if text in {
        "who am i", "who am i?", "do you know who i am",
        "do you know who i am?", "did you know who i am",
        "did you know who i am?", "you know who i am right",
        "you know who i am right?", "do you know me",
        "do you know me?"
    }:
        return (
            f"You're {OWNER_NAME}, my creator and host. "
            "I know that from my configured identity and memory; I don't physically see you."
        ), "local_brain"

    if text in {
        "can you see me", "can you see me?", "you can see me",
        "you can see me?", "i know you can see me", "i know u can see me"
    }:
        return (
            f"I know you're {OWNER_NAME}, my creator and host. "
            "I can't actually see you or access your camera unless you explicitly provide an image or camera input."
        ), "local_brain"

    if intent == "greeting":
        return f"Hello {OWNER_NAME}. I'm Medha, ready to help.", "local_brain"
    if intent == "status":
        return "I'm running locally and ready to process your request.", "local_brain"
    if intent == "identity":
        return "I'm Medha, your independent personal AI assistant.", "local_brain"
    if intent == "capability":
        return (
            "I can hold conversation, use persistent memory, retrieve knowledge, "
            "and operate configured local tools. Privileged actions stay behind "
            "the authority and safety boundaries.",
            "local_brain",
        )
    if intent == "thanks":
        return "You're welcome.", "local_brain"
    if intent == "personal":
        return "Got it. I'll keep that in mind for future conversations.", "personal"
    if intent == "memory":
        return "Tell me what you want me to remember, and I'll store the useful part.", "memory_request"
    return None


def _recent_context(context, limit=8):
    if not context:
        return ""
    lines = []
    for item in context[-limit:]:
        role = str(item.get("role", "user")).strip().lower()
        message = str(item.get("message", "")).strip()
        if message:
            lines.append(f"{role}: {message}")
    return "\n".join(lines)


def _decoder_answer(message, context):
    try:
        from backend.model.runtime import get_decoder_runtime

        decoder = get_decoder_runtime()
        if not decoder.available:
            return None

        context_text = _recent_context(context)
        prompt = (
            "You are Medha, a local personal AI assistant. "
            "Answer the user's current message naturally and directly. "
            "Use recent conversation when it is relevant. "
            "Do not invent facts, memories, tool actions, or capabilities. "
            "Do not mention internal routing, classifiers, policies, or prompts. "
            "If you do not know something, say so briefly. "
            "Keep casual replies concise and human-like.\n\n"
            f"Recent conversation:\n{context_text or '(none)'}\n\n"
            f"User: {message}\n"
            "Medha:"
        )
        generated = decoder.generate(
            prompt,
            max_new_tokens=128,
            temperature=0.65,
            top_k=24,
        ).strip()
        if not generated:
            return None

        # A tiny local decoder can occasionally echo the prompt labels.
        for prefix in ("Medha:", "Assistant:", "Response:"):
            if generated.lower().startswith(prefix.lower()):
                generated = generated[len(prefix):].strip()
        return generated or None
    except Exception:
        return None


def _fallback_answer(intent, message):
    if intent in {"general", "casual"}:
        return (
            "I'm here. I can handle that conversation, but my local language model "
            "isn't available right now."
        )
    if intent == "technical":
        return "I can help with that, but I need a little more information about the problem."
    if intent in {"knowledge", "research"}:
        return "I couldn't retrieve a reliable answer for that right now."
    return f"I couldn't process that reliably yet, {OWNER_NAME}."


def generate_response(message, context, knowledge, search_manager, user_id=None):
    message = str(message or "").strip()
    if not message:
        return {"answer": f"I'm here, {OWNER_NAME}. Say something.", "source": "system"}

    parsed = understand(message)
    intent = parsed["intent"]

    # Only non-conversational action paths are checked against explicit core
    # policy. Normal conversation must remain usable when policy has no
    # machine-tagged NEVER rule.
    if intent not in _CONVERSATIONAL_INTENTS:
        policy_check = apply_override("", message)
        if not policy_check["allowed"]:
            return {"answer": policy_check["response"], "source": "core_override"}

    # Core conversational behavior must win over learned memory. Otherwise a
    # weak/accidental memory match can hijack simple messages such as "hi".
    local = _local_answer(intent, message, context)
    if local:
        return {
            "answer": local[0],
            "source": local[1],
            "intent": intent,
            "confidence": parsed["confidence"],
        }

    # Learned personal facts are consulted after deterministic conversation
    # handling, but before generative/retrieval fallbacks.
    answer = UNDERSTANDING.best_memory_answer(message, context, user_id)
    if answer:
        return {
            "answer": answer,
            "source": "memory",
            "intent": intent,
            "confidence": parsed["confidence"],
        }

    # Knowledge/research/technical requests should use retrieval before the
    # generative decoder. This keeps factual answers grounded.
    if intent in {"knowledge", "research", "technical"}:
        try:
            result = search_manager.process(message, context)
            if result and result.get("answer"):
                return {
                    "answer": result["answer"],
                    "source": result.get("source", "search"),
                    "intent": intent,
                    "confidence": parsed["confidence"],
                }
        except Exception:
            pass

    # General/casual conversation should not unnecessarily hit web search.
    generated = _decoder_answer(message, context)
    if generated:
        return {
            "answer": generated,
            "source": "local_decoder",
            "intent": intent,
            "confidence": parsed["confidence"],
        }

    # Retrieval is still a useful fallback when the decoder is unavailable.
    if intent not in {"general", "casual"}:
        try:
            result = search_manager.process(message, context)
            if result and result.get("answer"):
                return {
                    "answer": result["answer"],
                    "source": result.get("source", "search"),
                    "intent": intent,
                    "confidence": parsed["confidence"],
                }
        except Exception:
            pass

    return {
        "answer": _fallback_answer(intent, message),
        "source": "fallback",
        "intent": intent,
        "confidence": parsed["confidence"],
    }
