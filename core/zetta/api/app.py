"""ZETTA API Application - FastAPI Server & Static UI Host."""

import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.zetta.api.routes import (
    agents_router,
    browser_router,
    chat_router,
    computer_router,
    confirmations_router,
    documents_router,
    memory_router,
    settings_router,
    skills_plugins_router,
    system_router,
    tasks_router,
    vision_router,
    voice_router,
    workflows_router,
)
from core.zetta.api.websocket import get_ws_manager
from core.zetta.utils.logging import get_logger

from contextlib import asynccontextmanager
from core.zetta.runtime import initialize_runtime

logger = get_logger("api_app")

UI_DIR = Path(__file__).resolve().parent.parent.parent.parent / "apps" / "desktop" / "ui"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Controlled application lifecycle startup and teardown."""
    initialize_runtime()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application for ZETTA Desktop."""
    # Ensure runtime is initialized idempotently
    initialize_runtime()

    app = FastAPI(
        title="ZETTA AI Employee API",
        description="REST and WebSocket Gateway for the ZETTA Desktop Interface",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Enable CORS for local desktop UI
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include Subsystem Routers
    app.include_router(system_router)
    app.include_router(chat_router)
    app.include_router(agents_router)
    app.include_router(tasks_router)
    app.include_router(workflows_router)
    app.include_router(computer_router)
    app.include_router(browser_router)
    app.include_router(vision_router)
    app.include_router(voice_router)
    app.include_router(memory_router)
    app.include_router(skills_plugins_router)
    app.include_router(confirmations_router)
    app.include_router(settings_router)
    app.include_router(documents_router)

    # WebSocket Real-Time Event Stream
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        ws_mgr = get_ws_manager()
        await ws_mgr.connect(websocket)
        try:
            while True:
                # Keep-alive / receive client pings or commands
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            ws_mgr.disconnect(websocket)
        except Exception as e:
            logger.debug(f"WebSocket client disconnected: {e}")
            ws_mgr.disconnect(websocket)

    # Mount UI Static Assets
    if UI_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")

        @app.get("/")
        async def serve_index():
            index_file = UI_DIR / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            return {"status": "ZETTA API Running. UI index.html not yet built."}

        # SPA Fallback for client routes
        @app.get("/{full_path:path}")
        async def catch_all(full_path: str):
            # If path points to an existing file in UI_DIR, serve it
            target = UI_DIR / full_path
            if target.is_file():
                return FileResponse(str(target))
            index_file = UI_DIR / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            return {"error": "Not Found", "path": full_path}

    return app


_app = None


def get_api_app() -> FastAPI:
    """Singleton getter for FastAPI app instance."""
    global _app
    if _app is None:
        _app = create_app()
    return _app


app = get_api_app()

