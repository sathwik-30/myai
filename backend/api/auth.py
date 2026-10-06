from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.auth.security import create_token, hash_password, verify_password
from backend.auth.dependencies import current_user
from backend.chats.store import create_user, get_user, has_admin, update_password
import hashlib
import secrets
import time
from collections import defaultdict, deque

from fastapi import Request

router = APIRouter(prefix="/auth", tags=["auth"])

_RATE_WINDOW_SECONDS = 60
_RATE_LIMIT = 8
_attempts = defaultdict(deque)

def _rate_limit(request: Request, bucket: str) -> None:
    now = time.monotonic()
    key = f"{bucket}:{request.client.host if request.client else 'unknown'}"
    queue = _attempts[key]
    while queue and now - queue[0] > _RATE_WINDOW_SECONDS:
        queue.popleft()
    if len(queue) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many authentication attempts. Try again later.")
    queue.append(now)


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    password: str = Field(..., min_length=8, max_length=128)


@router.post("/register")
def register(request: AuthRequest, request_context: Request):
    _rate_limit(request_context, "register")
    username = request.username.strip().lower()
    role = "creator" if not has_admin() else "user"
    recovery_code = secrets.token_urlsafe(18)
    recovery_code_hash = hashlib.sha256(recovery_code.encode()).hexdigest()
    user_id = create_user(
        username,
        hash_password(request.password),
        role=role,
        recovery_code_hash=recovery_code_hash,
    )
    if not user_id:
        raise HTTPException(status_code=409, detail="Username already exists")

    return {
        "token": create_token(user_id, username, role),
        "username": username,
        "role": role,
        "admin": role == "creator",
        "recovery_code": recovery_code,
    }


@router.post("/login")
def login(request: AuthRequest, request_context: Request):
    _rate_limit(request_context, "login")
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


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    recovery_code: str = Field(..., min_length=12, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/password/change")
def change_password(request: PasswordChangeRequest, user=Depends(current_user)):
    account = get_user(str(user["username"]).strip().lower())
    if not account or not verify_password(request.current_password, account["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if request.current_password == request.new_password:
        raise HTTPException(status_code=400, detail="New password must be different from the current password")
    update_password(account["id"], hash_password(request.new_password))
    return {"message": "Password changed successfully"}


@router.post("/password/reset")
def reset_password(request: PasswordResetRequest, request_context: Request):
    _rate_limit(request_context, "reset")
    username = request.username.strip().lower()
    account = get_user(username)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    stored = account.get("recovery_code_hash")
    if not stored:
        raise HTTPException(status_code=400, detail="This account does not have a recovery code. Generate one while signed in first.")
    supplied = hashlib.sha256(request.recovery_code.strip().encode()).hexdigest()
    if not secrets.compare_digest(supplied, stored):
        raise HTTPException(status_code=401, detail="Invalid recovery code")

    if not update_password(
        account["id"],
        hash_password(request.new_password),
        clear_recovery_code=True,
    ):
        raise HTTPException(status_code=500, detail="Could not reset password")

    return {"message": "Password reset successfully. The recovery code was used and is no longer valid."}


@router.post("/password/recovery-code")
def generate_recovery_code(user=Depends(current_user)):
    account = get_user(str(user["username"]).strip().lower())
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    recovery_code = secrets.token_urlsafe(18)
    recovery_code_hash = hashlib.sha256(recovery_code.encode()).hexdigest()
    if not update_password(account["id"], account["password_hash"], recovery_code_hash):
        raise HTTPException(status_code=500, detail="Could not generate recovery code")
    return {"recovery_code": recovery_code}
