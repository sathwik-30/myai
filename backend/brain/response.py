import re
from backend.brain.identity import OWNER_NAME,ASSISTANT_NAME

def words(text):
    return set(re.findall(r"\b\w+\b",text.lower()))

def is_greeting(text):
    greetings=[
        "hi",
        "hello",
        "hey",
        "hii",
        "hiii",
        "good morning",
        "good afternoon",
        "good evening"
    ]

    text=text.strip().lower()

    for greeting in greetings:
        if text==greeting or text.startswith(greeting+" "):
            return True

    return False

def is_owner_question(text):
    patterns=[
        "who am i",
        "do you know me",
        "who is your owner",
        "who's your owner",
        "who owns you"
    ]

    return any(pattern in text for pattern in patterns)

def is_identity_question(text):
    patterns=[
        "who are you",
        "what are you",
        "what is your name",
        "whats your name"
    ]

    return any(pattern in text for pattern in patterns)

def is_purpose_question(text):
    patterns=[
        "what is your purpose",
        "what's your purpose",
        "why do you exist",
        "what do you do"
    ]

    return any(pattern in text for pattern in patterns)

def is_memory_question(text):
    patterns=[
        "what did i say",
        "what did i tell you",
        "what did i ask",
        "what was my last question",
        "do you remember what i said"
    ]

    return any(pattern in text for pattern in patterns)

def is_thanks(text):
    return any(
        word in text
        for word in [
            "thank you",
            "thanks",
            "thank u",
            "thx"
        ]
    )

def is_how_are_you(text):
    patterns=[
        "how are you",
        "how r you",
        "how are u",
        "how're you"
    ]

    return any(pattern in text for pattern in patterns)

def is_question(text):
    question_words={
        "what",
        "why",
        "how",
        "when",
        "where",
        "who",
        "which",
        "whose",
        "can",
        "could",
        "would",
        "should",
        "is",
        "are",
        "do",
        "does",
        "did"
    }

    text_words=words(text)

    return "?" in text or bool(
        text_words.intersection(question_words)
    )

def format_wikipedia_result(search_result):
    if not search_result:
        return None

    result=search_result["results"][0]

    title=result.get("title","")

    snippet=result.get("snippet","")

    snippet=re.sub(
        "<.*?>",
        "",
        snippet
    )

    if not snippet:
        return None

    return (
        f"According to Wikipedia, {title} is "
        f"{snippet}"
    )

def generate_response(
    message,
    context,
    knowledge,
    search_manager
):
    text=message.strip().lower()

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
        user_messages=[
            item["message"]
            for item in context
            if item["role"]=="user"
        ]

        if len(user_messages)<2:
            return (
                "We haven't talked enough for "
                "me to recall an earlier message."
            )

        return (
            f"Your previous message was: "
            f"{user_messages[-2]}"
        )

    local_result=knowledge.search(message)

    if local_result:
        return local_result["content"]

    if is_question(text):
        search_result=search_manager.search(message)

        if search_result:
            if search_result["source"]=="wikipedia":
                answer=format_wikipedia_result(
                    search_result
                )

                if answer:
                    return answer

    return (
        f"I'm listening, {OWNER_NAME}. "
        f"Tell me more."
    )