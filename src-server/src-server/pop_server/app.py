"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pop_server.auth.routes import router as auth_router
from pop_server.billing.routes import router as billing_router
from pop_server.ai.routes import router as ai_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Path of Purpose API",
        description="Backend API for Path of Purpose — AI features, auth, and billing",
        version="0.1.0",
    )

    # CORS: allow the desktop app (localhost) and any future web frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Desktop app uses Tauri custom protocol
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(auth_router)
    app.include_router(billing_router)
    app.include_router(ai_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "path-of-purpose-api"}

    return app
