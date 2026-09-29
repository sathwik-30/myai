from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth.dependencies import current_user
from backend.core.authority import authority_for_user, authority_policy

router = APIRouter(prefix="/authority", tags=["authority"])


class PermissionUpdate(BaseModel):
    capability: str = Field(..., min_length=1, max_length=80)
    enabled: bool


@router.get("/status")
def authority_status(user=Depends(current_user)):
    actor = authority_for_user(user)
    return {
        **authority_policy.snapshot(),
        "requesting_principal": actor.__dict__.copy(),
    }


@router.post("/permissions")
def update_permission(request: PermissionUpdate, user=Depends(current_user)):
    actor = authority_for_user(user)
    if not authority_policy.can_configure(actor):
        raise HTTPException(status_code=403, detail="Creator/host authority required")
    authority_policy.set_permission(actor, request.capability, request.enabled)
    return authority_policy.snapshot()
