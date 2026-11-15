from __future__ import annotations

import redis
from fastapi import APIRouter, Depends
from qdrant_client import QdrantClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    settings = get_settings()
    db.execute(text("SELECT 1"))

    redis_status = "disconnected"
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1.5)
        if r.ping():
            redis_status = "connected"
        r.close()
    except Exception:
        redis_status = "unavailable"

    qdrant_status = "unavailable"
    try:
        qc = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
            timeout=2.0,
        )
        qc.get_collections()
        qdrant_status = "connected"
    except Exception:
        qdrant_status = "unavailable"

    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "database": "connected",
        "redis": redis_status,
        "qdrant": qdrant_status,
    }
