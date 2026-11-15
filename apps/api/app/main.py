from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import analysis, auth, curriculum, dashboard, documents, health, questions, rag, users
from app.core.config import get_settings
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    configure_logging()
    settings.validate_production_secrets()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.3.0-prep",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.API_V1_PREFIX
    app.include_router(health.router, prefix=prefix)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(dashboard.router, prefix=prefix)
    app.include_router(curriculum.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(rag.router, prefix=prefix)
    app.include_router(analysis.router, prefix=prefix)
    app.include_router(questions.router, prefix=prefix)

    return app


app = create_app()
