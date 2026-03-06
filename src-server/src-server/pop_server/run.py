"""Uvicorn entry point for the Path of Purpose API server."""

from __future__ import annotations

import uvicorn

from pop_server.app import create_app
from pop_server.config import settings

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "pop_server.run:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
    )
