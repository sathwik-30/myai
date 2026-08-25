import re

from backend.brain.identity import (
    OWNER_NAME,
    ASSISTANT_NAME
)

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

        if len(user_messages) < 2:
            return (
                "We haven't talked enough for "
                "me to recall an earlier message."
            )

        return (
            f"Your previous message was: "
            f"{user_messages[-2]}"
        )

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