def generate_response(
    message,
    context,
    knowledge,
    search_manager
):
    text = message.strip().lower()

    if not text:
        return f"I'm here, {OWNER_NAME}. Say something."

    if is_greeting(text):
        return (
            f"Hello {OWNER_NAME}. "
            f"I'm here. How are you?"
        )

    if is_owner_question(text):
        return f"You're {OWNER_NAME}, my owner."

    if is_identity_question(text):
        return (
            f"I'm {ASSISTANT_NAME}, "
            f"your personal assistant."
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

    # ------------------------------------------------
    # NEW INTELLIGENT PIPELINE
    # ------------------------------------------------

    result = search_manager.process(
        message,
        context
    )

    return result["answer"]