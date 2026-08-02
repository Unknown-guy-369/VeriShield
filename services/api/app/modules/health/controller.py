from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request

from app.dependencies import get_container

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health(request: Request) -> dict[str, Any]:
    container = get_container(request)
    return {
        "service": "verishield-api",
        "status": "ok",
        "persistence": "postgresql" if container.database else "memory",
        "timestamp": datetime.now(UTC).isoformat(),
    }
