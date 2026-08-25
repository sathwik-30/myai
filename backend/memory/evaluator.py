from backend.ai.model import generate_response


def evaluate_memory(
    question,
    answer
):
    """
    Ask Ollama whether the information should
    become long-term memory.
    """

    prompt = f"""
You are Medha's memory evaluator.

Decide whether this information is worth
remembering for future conversations.

User message:
{question}

Answer:
{answer}

Return ONLY JSON:

{{
    "save": true,
    "importance": 1,
    "memory_type": "preference"
}}

Rules:

importance:
1 = trivial / temporary
2 = mildly useful
3 = useful later
4 = important long-term
5 = critical identity, owner, security or major project information

memory_type must be one of:

identity
owner
preference
goal
project
instruction
knowledge
conversation
temporary

Do not save greetings, casual small talk,
repeated information or meaningless details.
"""

    result = generate_response(prompt)

    if not result:
        return None

    if result.get("status") != "answered":
        return None

    return result.get("answer")