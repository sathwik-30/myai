from fastapi import APIRouter
from pydantic import BaseModel
from backend.brain.conversation import ConversationEngine

router=APIRouter()

medha=ConversationEngine()

class ChatRequest(BaseModel):
    message:str

@router.post("/chat")
def chat(request:ChatRequest):
    response=medha.chat(
        request.message
    )

    return {
        "response":response
    }