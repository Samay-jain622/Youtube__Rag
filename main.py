"""ASGI entry point for the YouTube RAG API."""

import os

import uvicorn

from src.api.app import app
from src.utils.config import settings

__all__ = ["app"]


if __name__ == "__main__":
    reload_enabled = os.getenv("BACKEND_RELOAD", "true").lower() == "true"
    uvicorn.run(
        "main:app",
        host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        port=int(os.getenv("BACKEND_PORT", "9999")),
        reload=reload_enabled,
        workers=1 if reload_enabled else settings.backend_workers,
    )
