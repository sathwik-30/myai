from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

from backend.api.chat import router
from backend.api.auth import router as auth_router
from backend.api.chats import router as chats_router
from backend.api.desktop import router as desktop_router
from backend.api.authority import router as authority_router
from backend.auth.dependencies import current_user
from backend.chats.store import init_chat_tables
from backend.memory.layers import counts, delete_memory, list_memories, SCOPES
from backend.llm.router import router as model_router
from backend.core.authority import authority_policy
from backend.brain.local_nlu import get_language_engine
from backend.training.evaluate import checkpoint_exists, production_checkpoint_exists, promotion_status

app = FastAPI(
    title="Medha AI",
    version="1.5.0",
    description="Independent local personal AI system with identity, memory, tools, autonomy, and trainable local model foundations.",
)

allowed_origins = [item.strip() for item in os.getenv(
    "MEDHA_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",") if item.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(chats_router, prefix="/api")
app.include_router(desktop_router, prefix="/api")
app.include_router(authority_router, prefix="/api")
init_chat_tables()

@app.get("/")
def home():
    return {"service": "Medha", "status": "online", "version": app.version, "authority": "creator-host"}

@app.get("/api/memory")
def get_memory(memory_scope: str | None = None, limit: int = 100, user=Depends(current_user)):
    if memory_scope is not None and memory_scope not in SCOPES:
        raise HTTPException(status_code=400, detail="Invalid memory scope")
    user_id = int(user["sub"])
    limit = max(1, min(int(limit), 500))
    if memory_scope:
        memories = list_memories(memory_scope, user_id, limit)
    else:
        memories = []
        for scope in (SCOPES - {"knowledge"}):
            memories.extend(list_memories(scope, user_id, limit))
        memories.extend(list_memories("knowledge", user_id, limit))
    return {"count": len(memories), "memories": memories, "counts": counts(user_id)}

@app.delete("/api/memory/{memory_scope}/{memory_id}")
def remove_memory(memory_scope: str, memory_id: int, user=Depends(current_user)):
    if memory_scope not in SCOPES or memory_scope == "knowledge":
        raise HTTPException(status_code=400, detail="Only personal and temporary memory can be deleted here")
    if not delete_memory(memory_scope, int(user["sub"]), memory_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True, "memory_scope": memory_scope, "memory_id": memory_id}

@app.get("/api/health")
def health():
    nlu_available = get_language_engine().available
    try:
        from backend.llm.ollama import provider as ollama_provider
        ollama_available = ollama_provider.available()
    except Exception:
        ollama_available = False
    training_checkpoint = checkpoint_exists()
    production_model = production_checkpoint_exists()
    promotion = promotion_status()
    return {
        "status": "ok",
        "service": "medha-backend",
        "memory_layers": True,
        "runtime_model": "local-nlu",
        "ollama": ollama_available,
        "model_provider": model_router.provider_name,
        "runtime_nlu_available": nlu_available,
        "trainable_decoder_checkpoint": training_checkpoint,
        "decoder_promotion_eligible": promotion["eligible"],
        "model_available": production_model,
        "production_decoder_checkpoint": production_model,
        "authority": authority_policy.snapshot(),
    }
