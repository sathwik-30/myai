import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

REQUEST_TIMEOUT = 120


def generate_response(prompt):
    """
    Send a prompt to Ollama.

    Returns:
        dict:
            status:
                answered
                unknown
                refused
                unavailable
                timeout
                error
            answer:
                generated answer or None
            error:
                technical error message when applicable
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

        answer = result.get("response", "").strip()

        if not answer:
            return {
                "status": "unknown",
                "answer": None,
                "error": None
            }

        upper_answer = answer.upper().strip()

        # Ollama explicitly says it doesn't know.
        if upper_answer == "UNKNOWN":
            return {
                "status": "unknown",
                "answer": None,
                "error": None
            }

        # Basic refusal detection.
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
            "error": "Ollama is not running or cannot be reached."
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


def ask_ollama(question, context=""):
    """
    Ask Ollama whether it can answer the question.

    This function does NOT search the internet.
    SearchManager decides what to do when Ollama cannot answer.
    """

    prompt = f"""
You are Medha, a personal AI assistant.

Your job is to answer the user's question accurately.

Rules:

1. If you know the answer, answer clearly.
2. If you are genuinely uncertain or do not know,
   return exactly:
UNKNOWN
3. Do not invent facts.
4. Do not pretend to know current information that you cannot verify.
5. If the provided context contains useful information,
   use it.
6. Do not include UNKNOWN together with another answer.

Conversation context:
{context}

User question:
{question}

Answer:
"""

    return generate_response(prompt)


def answer_from_web(question, web_information):
    """
    Give externally collected information to Ollama
    and ask it to produce the final answer.
    """

    prompt = f"""
You are Medha.

The user asked:

{question}

The following information was collected from external sources:

{web_information}

Use the supplied information to answer the user's question.

Rules:

1. Do not invent facts.
2. Do not claim something is true if the supplied information
   does not support it.
3. If multiple sources disagree, explain the uncertainty.
4. Give a clear answer.
5. If the information is insufficient, return exactly:
UNKNOWN

Answer:
"""

    return generate_response(prompt)