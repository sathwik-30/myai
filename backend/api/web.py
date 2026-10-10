"""Authenticated web research endpoints for Medha."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from backend.auth.dependencies import current_user
from backend.agent.permissions import PermissionProfile
from backend.search.web import search_web

router = APIRouter(prefix="/web", tags=["web"])

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    limit: int = Field(default=5, ge=1, le=10)

def require_web_permission():
    if not PermissionProfile.from_policy().can("web"):
        raise HTTPException(status_code=403, detail="Web access is disabled by Medha's authority policy.")

@router.post("/search", dependencies=[Depends(require_web_permission)])
def web_search(request: SearchRequest, user=Depends(current_user)):
    results = search_web(request.query, request.limit)
    return {"query": request.query, "count": len(results), "results": results}
