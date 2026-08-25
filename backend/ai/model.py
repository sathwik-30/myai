import requests

OLLAMA_URL="http://localhost:11434/api/generate"
MODEL="llama3"

def generate_response(prompt):
    data={
        "model":MODEL,
        "prompt":prompt,
        "stream":False
    }

    response=requests.post(OLLAMA_URL,json=data)

    if response.status_code!=200:
        raise Exception(f"Ollama error: {response.text}")

    return response.json()["response"]