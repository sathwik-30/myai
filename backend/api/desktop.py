import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.auth.dependencies import current_user
from backend.desktop.agent import DesktopAgent, DesktopAgentError

router = APIRouter(prefix="/desktop", tags=["desktop"])
agent = DesktopAgent()


def _run(action):
    try:
        return action()
    except DesktopAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=500, detail="Desktop operation failed.") from None


class OpenAppRequest(BaseModel):
    app: str = Field(..., min_length=1, max_length=40)


class FocusWindowRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)


class ClickRequest(BaseModel):
    x: int
    y: int
    button: str = "left"


class TypeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    interval: float = Field(0.01, ge=0, le=0.2)


class HotkeyRequest(BaseModel):
    keys: list[str] = Field(..., min_length=1, max_length=6)


class ScrollRequest(BaseModel):
    clicks: int = Field(..., ge=-20, le=20)


@router.get("/status")
def desktop_status(user=Depends(current_user)):
    return _run(agent.status)


@router.get("/windows")
def desktop_windows(user=Depends(current_user)):
    return {"windows": _run(agent.windows)}


@router.post("/open")
def desktop_open(request: OpenAppRequest, user=Depends(current_user)):
    return _run(lambda: agent.open_app(request.app))


@router.post("/focus")
def desktop_focus(request: FocusWindowRequest, user=Depends(current_user)):
    return _run(lambda: agent.focus_window(request.title))


@router.post("/click")
def desktop_click(request: ClickRequest, user=Depends(current_user)):
    return _run(lambda: agent.click(request.x, request.y, request.button))


@router.post("/type")
def desktop_type(request: TypeRequest, user=Depends(current_user)):
    return _run(lambda: agent.type_text(request.text, request.interval))


@router.post("/hotkey")
def desktop_hotkey(request: HotkeyRequest, user=Depends(current_user)):
    return _run(lambda: agent.hotkey(request.keys))


@router.post("/scroll")
def desktop_scroll(request: ScrollRequest, user=Depends(current_user)):
    return _run(lambda: agent.scroll(request.clicks))


@router.get("/processes")
def desktop_processes(user=Depends(current_user)):
    return {"processes": _run(agent.processes)}


@router.get("/screenshot")
def desktop_screenshot(user=Depends(current_user)):
    fd, path = tempfile.mkstemp(prefix="medha-screen-", suffix=".png")
    os.close(fd)
    try:
        _run(lambda: agent.screenshot(path))
        return FileResponse(path, media_type="image/png", filename="medha-screen.png")
    except Exception:
        try:
            os.remove(path)
        except OSError:
            pass
        raise
