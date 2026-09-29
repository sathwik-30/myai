from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.auth.security import create_token, hash_password, verify_password
from backend.auth.dependencies import current_user\nfrom backend.chats.store import create_user, get_user, has_admin, update_password\nimport hashlib\nimport secrets

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    password: str = Field(..., min_length=8, max_length=128)


@router.post("/register")
def register(request: AuthRequest):
    username = request.username.strip().lower()
    role = "creator" if not has_admin() else "user"
    recovery_code = secrets.token_urlsafe(18)\n    recovery_code_hash = hashlib.sha256(recovery_code.encode()).hexdigest()\n    user_id = create_user(username, hash_password(request.password), role=role, recovery_code_hash=recovery_code_hash)
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
def reset_password(request: PasswordResetRequest):
    username = request.username.strip().lower()
    account = get_user(username)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    stored = account.get("recovery_code_hash")
    if not stored:
        raise HTTPException(status_code=400, detail="This account does not have a recovery code. Use password change while signed in.")
    supplied = hashlib.sha256(request.recovery_code.strip().encode()).hexdigest()
    if not secrets.compare_digest(supplied, stored):
        raise HTTPException(status_code=401, detail="Invalid recovery code")
    update_password(account["id"], hash_password(request.new_password), None)
    return {"message": "Password reset successfully. You can now sign in."}


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
