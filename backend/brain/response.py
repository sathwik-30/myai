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


# ============================================================
# BASIC INTENTS
# ============================================================

def is_greeting(text):
    return _matches(text, (
        r"^(hi|hello|hey|good (morning|afternoon|evening))\b",
    ))


def is_owner_question(text):
    return _matches(text, (
        r"\b(who|what)(?:'s| is) (your )?(owner|master)\b",
        r"\bwho (owns|created) you\b",
        r"\bwho made you\b",
        r"\bwho built you\b",
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
        r"\bhow r u\b",
        r"\bhow ru\b",
    ))


def is_thanks(text):
    return _matches(text, (
        r"\b(thanks|thank you|thx|ty)\b",
    ))


# ============================================================
# CASUAL CONVERSATION
# ============================================================

def is_casual_response(text):
    """
    Detect normal conversational replies.

    Handles both normal English and common informal
    texting such as:
        wt abt u
        wbu
        how r u
    """

    return _matches(text, (

        # Simple responses
        r"^(fine|good|great|okay|ok|alright)$",

        r"^(doing good|doing fine|not bad|pretty good)$",

        r"^(i am fine|i'm fine|im fine)$",
        r"^(i am good|i'm good|im good)$",
        r"^(i am okay|i'm okay|im okay)$",
        r"^(i am alright|i'm alright|im alright)$",

        # "fine, what about you?"
        r"^(fine|good|great)[, ]+"
        r"(what about you|how about you|wt abt u|wbu)\??$",

        # "I am fine, what about you?"
        r"^(i am fine|i'm fine|im fine)[, ]+"
        r"(what about you|how about you|wt abt u|wbu)\??$",

        # "I am good, what about you?"
        r"^(i am good|i'm good|im good)[, ]+"
        r"(what about you|how about you|wt abt u|wbu)\??$",

        # "doing good wbu"
        r"^(doing good|doing fine)[, ]+"
        r"(what about you|how about you|wt abt u|wbu)\??$",
    ))


def is_asking_about_medha(text):
    """
    Detect conversational questions directed at Medha.

    These should go directly to Ollama.
    """

    return _matches(text, (
        r"\bwhat about you\b",
        r"\bhow about you\b",
        r"\bwt abt u\b",
        r"\bwbu\b",
        r"\bwhat do you think\b",
        r"\bwhat do you prefer\b",
        r"\bwhat do you like\b",
        r"\bdo you like\b",
        r"\bdo you want\b",
        r"\bwould you like\b",
        r"\bhow do you feel\b",
        r"\btell me about yourself\b",
        r"\babout yourself\b",
        r"\babout you\b",
    ))


# ============================================================
# PERSONAL CONVERSATION
# ============================================================

def is_personal_conversation(text):
    """
    Detect conversations about Medha herself,
    her preferences, personality, naming, ideas,
    or the relationship with her owner.

    These go directly to Ollama.
    """

    return _matches(text, (

        # Asking Medha something
        r"\bi want to ask you\b",
        r"\bi wanted to ask you\b",

        # Naming
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
        r"\bif you could choose\b",

        # Preferences
        r"\bwhat do you like\b",
        r"\bwhat do you prefer\b",
        r"\bdo you like\b",
        r"\bdo you want\b",
        r"\bwould you like\b",
        r"\bwhat do you think\b",

        # About Medha
        r"\btell me about yourself\b",
        r"\btell me about you\b",
        r"\babout yourself\b",
        r"\babout you\b",

        # Relationship / creator conversation
        r"\byou are my assistant\b",
        r"\byou're my assistant\b",
        r"\bi am your creator\b",
        r"\bi'm your creator\b",
        r"\bi created you\b",
        r"\bi made you\b",
    ))


# ============================================================
# MEMORY QUESTIONS
# ============================================================

def is_memory_question(text):
    return _matches(text, (
        r"\b(what|do you).*(remember|recall)\b",
        r"\bmy (previous|last) message\b",
        r"\bdo you remember\b",
    ))


# ============================================================
# PERSONAL OLLAMA
# ============================================================

def _ask_personally(
    message,
    context,
    memory_manager
):
    """
    Send personal conversation directly to Ollama.

    No Wikipedia.
    No web search.

    The resulting conversation is saved so useful
    information can be recalled later.
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

        # Save the conversation.
        try:

            memory_manager.learn(
                message,
                answer,
                "conversation"
            )

            print(
                "[Medha] Learned conversation: "
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


# ============================================================
# MAIN RESPONSE GENERATOR
# ============================================================

def generate_response(
    message,
    context,
    knowledge,
    search_manager
):

    text = message.strip().lower()

    if not text:
        return (
            f"I'm here, {OWNER_NAME}. "
            "Say something."
        )

    # ========================================================
    # BASIC CONVERSATION
    # ========================================================

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

    # ========================================================
    # CASUAL CONVERSATION
    # ========================================================

    if is_casual_response(text):

        # User is answering Medha's question and
        # asking how Medha is doing.
        if _matches(text, (
            r"\bwhat about you\b",
            r"\bhow about you\b",
            r"\bwt abt u\b",
            r"\bwbu\b",
        )):

            return (
                "I'm functioning normally and "
                f"I'm ready to talk with you, {OWNER_NAME}."
            )

        return (
            f"Good to hear that, {OWNER_NAME}. "
            "What are we working on?"
        )

    # ========================================================
    # QUESTIONS ABOUT MEDHA
    # ========================================================

    if is_asking_about_medha(text):

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

    # ========================================================
    # PERSONAL CONVERSATION
    # ========================================================

    if is_personal_conversation(text):

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

    # ========================================================
    # CONVERSATION MEMORY
    # ========================================================

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

    # ========================================================
    # INTELLIGENT KNOWLEDGE PIPELINE
    # ========================================================
    #
    # At this point this is treated as a knowledge request.
    #
    # SearchManager:
    #
    # Memory
    #    ↓
    # Ollama
    #    ↓
    # Wikipedia
    #    ↓
    # Web
    #    ↓
    # Ollama
    #    ↓
    # Learn
    #
    # ========================================================

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

    # ========================================================
    # FINAL FALLBACK
    # ========================================================

    return (
        f"I'm unable to find a reliable answer "
        f"right now, {OWNER_NAME}."
    )