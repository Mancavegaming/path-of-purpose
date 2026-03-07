"""Uvicorn entry point for the Path of Purpose API server."""

from __future__ import annotations

import asyncio
import logging
import sys
import uvicorn

from pop_server.app import create_app
from pop_server.config import settings

# Suppress WinError 64 "network name no longer available" on Windows
# This happens when clients disconnect abruptly (common with desktop apps)
if sys.platform == "win32":
    _orig_exception_handler = None

    def _windows_exception_handler(loop: asyncio.AbstractEventLoop, context: dict):
        exception = context.get("exception")
        if isinstance(exception, OSError) and getattr(exception, "winerror", None) == 64:
            logging.getLogger("uvicorn").debug("Suppressed WinError 64 (client disconnected)")
            return
        if _orig_exception_handler:
            _orig_exception_handler(loop, context)
        else:
            loop.default_exception_handler(context)

    def _patch_event_loop():
        loop = asyncio.get_event_loop()
        global _orig_exception_handler
        _orig_exception_handler = loop.get_exception_handler()
        loop.set_exception_handler(_windows_exception_handler)

app = create_app()


@app.on_event("startup")
async def _on_startup():
    if sys.platform == "win32":
        _patch_event_loop()


if __name__ == "__main__":
    uvicorn.run(
        "pop_server.run:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
    )
