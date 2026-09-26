import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.brain.conversation import ConversationEngine

router = APIRouter()
medha = ConversationEngine()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    response: str
    source: str = "medha"
    latency_ms: int


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    started = time.perf_counter()

    try:
        result = medha.chat(request.message.strip())
        response = result["response"] if isinstance(result, dict) else str(result)
        source = result.get("source", "medha") if isinstance(result, dict) else "medha"

        return ChatResponse(
            response=response,
            source=source,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )
    except Exception as error:
        print(f"[Chat] Error: {error}")
        raise HTTPException(
            status_code=500,
            detail="Medha encountered an internal error while processing the message.",
        )
