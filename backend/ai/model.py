import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

REQUEST_TIMEOUT = 120


def generate_response(prompt):
    """
    Send a prompt to Ollama.

    Returns:
        dict with:
            status
            answer
            error
    """

    data = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=data,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        result = response.json()

        answer = result.get(
            "response",
            ""
        ).strip()

        if not answer:
            return {
                "status": "unknown",
                "answer": None,
                "error": None
            }

        upper_answer = answer.upper().strip()

        if upper_answer == "UNKNOWN":
            return {
                "status": "unknown",
                "answer": None,
                "error": None
            }

        refusal_phrases = [
            "I can't help with that",
            "I cannot help with that",
            "I can't assist with that",
            "I cannot assist with that",
            "I can't provide instructions",
            "I cannot provide instructions"
        ]

        if any(
            phrase.lower() in answer.lower()
            for phrase in refusal_phrases
        ):
            return {
                "status": "refused",
                "answer": answer,
                "error": None
            }

        return {
            "status": "answered",
            "answer": answer,
            "error": None
        }

    except requests.exceptions.ConnectionError:
        return {
            "status": "unavailable",
            "answer": None,
            "error": (
                "Ollama is not running "
                "or cannot be reached."
            )
        }

    except requests.exceptions.Timeout:
        return {
            "status": "timeout",
            "answer": None,
            "error": "Ollama request timed out."
        }

    except requests.exceptions.HTTPError as error:
        return {
            "status": "error",
            "answer": None,
            "error": f"Ollama HTTP error: {error}"
        }

    except requests.exceptions.RequestException as error:
        return {
            "status": "error",
            "answer": None,
            "error": f"Ollama request error: {error}"
        }

    except Exception as error:
        return {
            "status": "error",
            "answer": None,
            "error": f"Unexpected Ollama error: {error}"
        }


def ask_ollama(
    question,
    context=""
):
    """
    Knowledge mode.

    If Ollama doesn't know, it returns UNKNOWN.
    SearchManager can then use Wikipedia/web.
    """

    prompt = f"""
You are Medha, a personal AI assistant.

The user is asking a knowledge or factual question.

Rules:

1. Answer accurately.
2. If you genuinely do not know the answer,
   return exactly:

UNKNOWN

3. Never invent facts.
4. Do not pretend to know current information
   that requires verification.
5. Use the supplied conversation context when useful.

Conversation context:
{context}

User question:
{question}

Answer:
"""

    return generate_response(prompt)


def chat_with_ollama(
    message,
    context=""
):
    """
    Conversation mode.

    This mode is for personal, casual and conversational
    messages.

    It does NOT use the UNKNOWN rule.
    It does NOT search the internet.
    """

    prompt = f"""
You are Medha, a personal AI assistant.

You are having a direct conversation with your owner,
Sathwik.

Respond naturally and intelligently.

You may discuss:

- yourself
- your preferences
- possible names for yourself
- personality
- ideas
- opinions
- casual conversation
- creative topics
- conversations about your relationship with your owner
- plans and goals

Do not claim to have human consciousness or feelings.
However, you may express reasonable preferences or
choices as part of the conversation.

Do not search the internet.
Do not return UNKNOWN merely because the conversation
is subjective or personal.

Use the conversation context to maintain continuity.

Conversation context:
{context}

User:
{message}

Medha:
"""

    return generate_response(prompt)


def answer_from_web(
    question,
    web_information
):
    """
    Give externally collected information to Ollama
    and ask it to produce the final answer.
    """

    prompt = f"""
You are Medha.

The user asked:

{question}

The following information was collected from
external sources:

{web_information}

Use the supplied information to answer the question.

Rules:

1. Do not invent facts.
2. Do not claim something is true if the supplied
   information does not support it.
3. If multiple sources disagree, explain the uncertainty.
4. Give a clear answer.
5. If the information is insufficient, return exactly:

UNKNOWN

Answer:
"""

    return generate_response(prompt)