import re

from backend.brain.identity import (
    OWNER_NAME,
    ASSISTANT_NAME
)


def _matches(text, patterns):
    """Return whether *text* matches one of the complete intent patterns."""
    return any(re.search(pattern, text) for pattern in patterns)


def is_greeting(text):
    return _matches(text, (
        r"^(hi|hello|hey|good (morning|afternoon|evening))\b",
    ))


def is_owner_question(text):
    return _matches(text, (
        r"\b(who|what)(?:'s| is) (your )?(owner|master)\b",
        r"\bwho (owns|created) you\b",
    ))


def is_identity_question(text):
    return _matches(text, (
        r"\bwho (are|r) you\b",
        r"\bwhat(?:'s| is) your name\b",
    ))


def is_purpose_question(text):
    return _matches(text, (
        r"\bwhat (?:is )?your purpose\b",
        r"\bwhat (?:can|do) you do\b",
    ))


def is_how_are_you(text):
    return _matches(text, (
        r"\bhow are you\b",
        r"\bhow(?:'s| is) it going\b",
    ))


def is_thanks(text):
    return _matches(text, (
        r"\b(thanks|thank you|thx)\b",
    ))


def is_memory_question(text):
    return _matches(text, (
        r"\b(what|do you).*(remember|recall)\b",
        r"\bmy (previous|last) message\b",
    ))


def generate_response(
    message,
    context,
    knowledge,
    search_manager
):
    text = message.strip().lower()

    if not text:
        return f"I'm here, {OWNER_NAME}. Say something."

    # -----------------------------
    # Basic conversation
    # -----------------------------

    if is_greeting(text):
        return (
            f"Hello {OWNER_NAME}. "
            "I'm here. How are you?"
        )

    if is_owner_question(text):
        return f"You're {OWNER_NAME}, my owner."

    if is_identity_question(text):
        return (
            f"I'm {ASSISTANT_NAME}, "
            "your personal assistant."
        )

    if is_purpose_question(text):
        return (
            f"My purpose is to assist you, "
            f"{OWNER_NAME}, and help with your work."
        )

    if is_how_are_you(text):
        return (
            "I'm functioning normally and "
            "I'm ready to talk with you."
        )

    if is_thanks(text):
        return "You're welcome."

    # -----------------------------
    # Conversation memory
    # -----------------------------

    if is_memory_question(text):

        user_messages = [
            item["message"]
            for item in context
            if item["role"] == "user"
        ]

        # The current message is added to the context after this function
        # returns, so the latest stored user message is the previous one.
        if not user_messages:
            return (
                "We haven't talked enough for "
                "me to recall an earlier message."
            )

        return (
            f"Your previous message was: "
            f"{user_messages[-1]}"
        )

    # Prefer the project's local knowledge base.  It works without Ollama or
    # an internet connection and avoids sending known questions through the
    # slower external search pipeline.
    if knowledge:
        local_knowledge = knowledge.search(message)

        if local_knowledge:
            return local_knowledge.get("content", "")

    # -----------------------------
    # Intelligent question pipeline
    # -----------------------------

    try:
        result = search_manager.process(
            message,
            context
        )

        if result and result.get("answer"):
            return result["answer"]

    except Exception as error:
        print(
            f"[Medha] Response pipeline error: {error}"
        )

    # -----------------------------
    # Final fallback
    # -----------------------------

    return (
        f"I'm unable to find a reliable answer "
        f"right now, {OWNER_NAME}."
    )
