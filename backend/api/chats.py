from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth.dependencies import current_user
from backend.chats.store import (
    create_chat, list_chats, get_chat, list_messages, add_message,
    rename_chat, delete_chat,
)

router = APIRouter(prefix="/chats", tags=["chats"])

class ChatCreate(BaseModel):
    title: str = Field(default="New chat", max_length=120)

class ChatRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)

class MessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    message: str = Field(..., min_length=1, max_length=8000)
    source: str = ""
    latency_ms: int = 0

def uid(user):
    return int(user["sub"])

@router.get("")
def chats(user=Depends(current_user)):
    return {"chats": list_chats(uid(user))}

@router.post("")
def new_chat(request: ChatCreate, user=Depends(current_user)):
    return {"chat_id": create_chat(uid(user), request.title)}

@router.get("/{chat_id}")
def chat(chat_id: int, user=Depends(current_user)):
    messages = list_messages(uid(user), chat_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    item = get_chat(uid(user), chat_id)
    return {"chat": item, "messages": messages}

@router.post("/{chat_id}/messages")
def message(chat_id: int, request: MessageCreate, user=Depends(current_user)):
    if not add_message(uid(user), chat_id, request.role, request.message, request.source, request.latency_ms):
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"saved": True}

@router.patch("/{chat_id}")
def rename(chat_id: int, request: ChatRename, user=Depends(current_user)):
    if not rename_chat(uid(user), chat_id, request.title):
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"updated": True}

@router.delete("/{chat_id}")
def remove(chat_id: int, user=Depends(current_user)):
    if not delete_chat(uid(user), chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"deleted": True}
