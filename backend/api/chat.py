import logging
import time
import traceback

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth.dependencies import current_user
from backend.brain.conversation import ConversationEngine
from backend.chats.store import add_message, list_messages

router = APIRouter()
logger = logging.getLogger("medha.chat")

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

    engine = ConversationEngine(user_id=user_id)
    for item in history[-20:]:
        engine.context.add(item["role"], item["message"])

    try:
        # Persist the user turn before generation. If generation fails, the
        # user message still remains in the permanent conversation history.
        if not add_message(user_id, request.chat_id, "user", request.message, "user", 0):
            raise HTTPException(status_code=404, detail="Chat not found")

        try:
            result = engine.chat(request.message)
            response = result["response"] if isinstance(result, dict) else str(result)
            source = result.get("source", "medha") if isinstance(result, dict) else "medha"
        except Exception:
            logger.error("Response generation failed for chat_id=%s", request.chat_id)
            logger.error(traceback.format_exc())
            raise

        latency = round((time.perf_counter() - started) * 1000)

        # The assistant turn is part of the durable chat history. Do not
        # return success until it has actually been written to SQLite.
        if not add_message(user_id, request.chat_id, "assistant", response, source, latency):
            raise RuntimeError("Assistant response could not be persisted")

        return ChatResponse(
            response=response,
            source=source,
            latency_ms=latency,
            chat_id=request.chat_id,
        )
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Chat request failed: %s", error)
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail="Medha encountered an internal error. The user message was preserved; retrying is safe.",
        )
