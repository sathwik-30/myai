from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.auth.security import create_token, hash_password, verify_password
from backend.chats.store import create_user, get_user, has_admin

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    password: str = Field(..., min_length=8, max_length=128)


@router.post("/register")
def register(request: AuthRequest):
    username = request.username.strip().lower()
    role = "creator" if not has_admin() else "user"
    user_id = create_user(username, hash_password(request.password), role=role)
    if not user_id:
        raise HTTPException(status_code=409, detail="Username already exists")

    return {
        "token": create_token(user_id, username, role),
        "username": username,
        "role": role,
        "admin": role == "creator",
    }


@router.post("/login")
def login(request: AuthRequest):
    username = request.username.strip().lower()
    user = get_user(username)
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {
        "token": create_token(user["id"], user["username"], user["role"]),
        "username": user["username"],
        "role": user["role"],
        "admin": user["role"] in {"admin", "creator", "host"},
    }
