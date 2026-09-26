from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.api.chat import router
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


@app.get("/")
def home():
    return {
        "service": "Medha",
        "status": "online",
        "version": app.version,
    }



@app.get("/api/memory")
def get_memory(memory_type: str | None = None, limit: int = 100):
    return {
        "count": memory_count(),
        "memories": list_memories(memory_type=memory_type, limit=limit),
    }


@app.delete("/api/memory/{memory_id}")
def remove_memory(memory_id: int):
    if not delete_memory(memory_id):
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
