"""Browser Center routes controlling web automation via BrowserManager."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.zetta.browser import get_browser_manager

router = APIRouter(prefix="/api/browser", tags=["Browser"])


class LaunchRequest(BaseModel):
    headless: bool = True
    use_fake: bool = False


class NavigateRequest(BaseModel):
    url: str
    session_id: Optional[str] = None


class ClickRequest(BaseModel):
    target: str
    session_id: Optional[str] = None


class TypeRequest(BaseModel):
    target: str
    text: str
    session_id: Optional[str] = None


class SessionCloseRequest(BaseModel):
    session_id: Optional[str] = None


@router.get("/status")
def get_browser_status():
    """Return browser subsystem status and installed browser binaries."""
    bm = get_browser_manager()
    st = bm.status()
    st["status"] = "ready" if st.get("is_available") else "offline"
    st["is_open"] = len(st.get("active_sessions", [])) > 0
    return st


@router.post("/launch")
def launch_browser(req: LaunchRequest):
    """Launch a browser session."""
    bm = get_browser_manager(use_fake=req.use_fake)
    try:
        session = bm.launch(headless=req.headless)
        return {
            "session_id": session.session_id,
            "browser_type": session.browser_type,
            "active_tab_id": session.active_tab_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/navigate")
def navigate_to_url(req: NavigateRequest):
    """Navigate current browser session to URL."""
    bm = get_browser_manager()
    try:
        page = bm.navigate(url=req.url, session_id=req.session_id)
        return page.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/page")
def get_page_info(session_id: Optional[str] = None):
    """Fetch active webpage info and detected clickable elements."""
    bm = get_browser_manager()
    try:
        page = bm.get_page_info(session_id=session_id)
        elements = bm.detect_elements(session_id=session_id)
        return {
            "page": page.to_dict(),
            "elements_count": len(elements),
            "elements": [e.to_dict() for e in elements[:50]],  # Cap for UI response
        }
    except Exception as e:
        return {"error": str(e), "page": None, "elements": []}


@router.post("/click")
def click_element(req: ClickRequest):
    """Click an element by selector, ID, or text."""
    bm = get_browser_manager()
    try:
        res = bm.click(target=req.target, session_id=req.session_id)
        return res.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/type")
def type_into_element(req: TypeRequest):
    """Type text into an input field."""
    bm = get_browser_manager()
    try:
        res = bm.type_text(target=req.target, text=req.text, session_id=req.session_id)
        return res.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/close")
def close_browser(req: SessionCloseRequest):
    """Close browser session."""
    bm = get_browser_manager()
    try:
        res = bm.close(session_id=req.session_id)
        return {"success": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
