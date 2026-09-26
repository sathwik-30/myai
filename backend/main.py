from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.api.chat import router
from backend.api.auth import router as auth_router
from backend.api.chats import router as chats_router
from backend.auth.dependencies import current_user
from backend.chats.store import init_chat_tables
from backend.memory.semantic_memory import count as memory_count, list_memories, delete_memory

app = FastAPI(
    title="Medha AI",
    version="1.1.0",
    description="Local personal AI assistant backend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(chats_router, prefix="/api")
init_chat_tables()


@app.get("/")
def home():
    return {
        "service": "Medha",
        "status": "online",
        "version": app.version,
    }



@app.get("/api/memory")
def get_memory(memory_type: str | None = None, limit: int = 100, user=Depends(current_user)):
    user_id = int(user["sub"])
    return {
        "count": len(list_memories(memory_type=memory_type, limit=limit, user_id=user_id)),
        "memories": list_memories(memory_type=memory_type, limit=limit, user_id=user_id),
    }


@app.delete("/api/memory/{memory_id}")
def remove_memory(memory_id: int, user=Depends(current_user)):
    if not delete_memory(memory_id, user_id=int(user["sub"])):
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True, "memory_id": memory_id}

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "medha-backend",
        "memory_count": memory_count(),
        "runtime_model": "local-memory",
        "ollama": False,
    }
