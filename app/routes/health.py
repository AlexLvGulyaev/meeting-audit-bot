from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.runtime_config import RuntimeConfig
from app.services.storage import StorageService

router = APIRouter()


@router.get("/health", tags=["health"])
async def health() -> dict:
    return {
        "status": "ok",
        "service": "meeting-audit-bot",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/db", tags=["health"])
async def health_db() -> dict:
    storage = StorageService()
    db_ok = storage.health_check()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unreachable",
    }
