"""FastAPI application factory."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.api.routes import router
from src.models.database import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="YouTube RAG API",
        version="2.0.0",
        lifespan=lifespan,
    )
    application.include_router(router)
    return application


app = create_app()
