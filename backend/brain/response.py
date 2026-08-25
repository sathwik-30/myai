import re

from backend.brain.identity import (
    OWNER_NAME,
    ASSISTANT_NAME
)

from backend.ai.model import (
    chat_with_ollama
)


def _matches(text, patterns):
    """Return whether text matches one of the intent patterns."""
    return any(
        re.search(pattern, text)
        for pattern in patterns
    )


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


def is_casual_response(text):
    return _matches(text, (
        r"^(fine|good|great|okay|ok|alright)$",
        r"^(doing good|doing fine|not bad|pretty good)$",
        r"^(i am fine|i'm fine)$",
        r"^(i am good|i'm good)$",
        r"^(i am okay|i'm okay)$",
        r"^(i am alright|i'm alright)$",
    ))


def is_personal_conversation(text):
    """
    Detect personal/conversational messages.

    These should go directly to Ollama rather than
    Wikipedia or web search.
    """

    return _matches(text, (
        r"\bi want to ask you\b",
        r"\bwhich name do you like\b",
        r"\bwhat name do you like\b",
        r"\bwhat name would you like\b",
        r"\bwhat should i call you\b",
        r"\bwhat can i call you\b",
        r"\bdo you like the name\b",
        r"\bchoose a name\b",
        r"\bpick a name\b",
        r"\bgive you a name\b",
        r"\bname you\b",
        r"\bwhat would you like to be called\b",
        r"\bwhat do you think\b",
        r"\bwhat do you prefer\b",
        r"\bdo you like\b",
        r"\bdo you want\b",
        r"\bwould you like\b",
        r"\bif you could choose\b",
        r"\btell me about yourself\b",
        r"\babout yourself\b",
        r"\babout you\b",
    ))


def is_memory_question(text):
    return _matches(text, (
        r"\b(what|do you).*(remember|recall)\b",
        r"\bmy (previous|last) message\b",
    ))


def _ask_personally(
    message,
    context,
    memory_manager
):
    """
    Ask Ollama directly for personal conversation.

    The answer is also saved to memory so Medha can
    remember the conversation later.
    """

    try:
        result = chat_with_ollama(
            message,
            context
        )

        if not result:
            return None

        if result.get("status") != "answered":
            return None

        answer = result.get(
            "answer"
        )

        if not answer:
            return None

        # Save the conversation as personal memory.
        try:
            memory_manager.learn(
                message,
                answer,
                "conversation"
            )

            print(
                f"[Medha] Learned conversation: "
                f"{message}"
            )

        except Exception as memory_error:
            print(
                "[Memory] Failed to save "
                f"conversation: {memory_error}"
            )

        return answer

    except Exception as error:
        print(
            "[Medha] Personal conversation error: "
            f"{type(error).__name__}: {error}"
        )

        return None


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
        return (
            f"You're {OWNER_NAME}, "
            "my owner."
        )

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
    # Simple casual conversation
    # -----------------------------

    if is_casual_response(text):
        return (
            f"Good to hear that, {OWNER_NAME}. "
            "What are we working on?"
        )

    # -----------------------------
    # Personal conversation
    # -----------------------------

    if is_personal_conversation(text):

        # Import here to avoid unnecessary
        # dependency problems during startup.
        from backend.memory.manager import (
            MemoryManager
        )

        memory_manager = MemoryManager()

        personal_answer = _ask_personally(
            message,
            context,
            memory_manager
        )

        if personal_answer:
            return personal_answer

    # -----------------------------
    # Conversation memory
    # -----------------------------

    if is_memory_question(text):

        user_messages = [
            item["message"]
            for item in context
            if item["role"] == "user"
        ]

        if not user_messages:
            return (
                "We haven't talked enough for "
                "me to recall an earlier message."
            )

        return (
            f"Your previous message was: "
            f"{user_messages[-1]}"
        )

    # -----------------------------
    # Intelligent knowledge pipeline
    # -----------------------------

    try:
        result = search_manager.process(
            message,
            context
        )

        if result:
            answer = result.get(
                "answer"
            )

            if answer:
                return answer

    except Exception as error:
        print(
            "[Medha] Response pipeline error: "
            f"{type(error).__name__}: {error}"
        )

    # -----------------------------
    # Final fallback
    # -----------------------------

    return (
        f"I'm unable to find a reliable answer "
        f"right now, {OWNER_NAME}."
    )