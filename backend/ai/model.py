import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"


def generate_response(prompt):
    data = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(
        OLLAMA_URL,
        json=data,
        timeout=120
    )

    response.raise_for_status()

    return response.json()["response"].strip()


def ask_ollama(question, context=""):
    prompt = f"""
You are Medha, a personal AI assistant.

Answer the user's question using your knowledge and the provided context.

IMPORTANT:
- Do not invent facts.
- If you genuinely do not know the answer, return exactly:
UNKNOWN
- If the context contains the answer, use it.
- Give a clear and useful answer when you know it.

Context:
{context}

User question:
{question}

Answer:
"""

    answer = generate_response(prompt)

    if answer.strip().upper() == "UNKNOWN":
        return None

    return answer


def answer_from_web(question, web_information):
    prompt = f"""
You are Medha.

Answer the user's question using the information collected from external
sources.

Do not invent information that is not supported by the supplied information.

User question:
{question}

External information:
{web_information}

Give a clear, accurate answer.
"""

    return generate_response(prompt)