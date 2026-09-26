from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.chat import router
from backend.memory.semantic_memory import count as memory_count

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


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "medha-backend",
        "memory_count": memory_count(),
        "runtime_model": "local-memory",
        "ollama": False,
    }
