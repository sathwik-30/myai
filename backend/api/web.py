"""Authenticated web research endpoints for Medha."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from backend.auth.dependencies import current_user
from backend.agent.permissions import PermissionProfile
from backend.search.web import search_web, open_web_page

router = APIRouter(prefix="/web", tags=["web"])

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    limit: int = Field(default=5, ge=1, le=10)

class OpenRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048)

def require_web_permission():
    if not PermissionProfile.from_policy().can("web"):
        raise HTTPException(status_code=403, detail="Web access is disabled by Medha's authority policy.")

@router.post("/search", dependencies=[Depends(require_web_permission)])
def web_search(request: SearchRequest, user=Depends(current_user)):
    results = search_web(request.query, request.limit)
    return {"query": request.query, "count": len(results), "results": results}

@router.post("/open", dependencies=[Depends(require_web_permission)])
def web_open(request: OpenRequest, user=Depends(current_user)):
    try:
        page = open_web_page(request.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=502, detail="Could not retrieve that public webpage.") from None
    return page
