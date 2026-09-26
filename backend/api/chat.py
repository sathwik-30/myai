import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth.dependencies import current_user
from backend.brain.conversation import ConversationEngine
from backend.chats.store import add_message, list_messages

router = APIRouter()

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    chat_id: int

class ChatResponse(BaseModel):
    response: str
    source: str = "medha"
    latency_ms: int
    chat_id: int

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, user=Depends(current_user)):
    started = time.perf_counter()
    user_id = int(user["sub"])
    history = list_messages(user_id, request.chat_id)

    if history is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    engine = ConversationEngine()
    for item in history[-20:]:
        engine.context.add(item["role"], item["message"])

    try:
        add_message(user_id, request.chat_id, "user", request.message, "user", 0)
        result = engine.chat(request.message)
        response = result["response"] if isinstance(result, dict) else str(result)
        source = result.get("source", "medha") if isinstance(result, dict) else "medha"
        latency = round((time.perf_counter() - started) * 1000)
        add_message(user_id, request.chat_id, "assistant", response, source, latency)

        return ChatResponse(
            response=response,
            source=source,
            latency_ms=latency,
            chat_id=request.chat_id,
        )
    except Exception as error:
        print(f"[Chat] Error: {error}")
        raise HTTPException(status_code=500, detail="Medha encountered an internal error.")
