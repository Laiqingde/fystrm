from __future__ import annotations

from fastapi import APIRouter

from fystrm.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/")
async def get_settings() -> dict:
    return {
        "tmdb_configured": bool(settings.tmdb_api_key),
        "tmdb_language": settings.tmdb_language,
        "emby_configured": bool(settings.emby_url and settings.emby_api_key),
        "emby_url": settings.emby_url or None,
        "log_level": settings.log_level,
        "debug": settings.debug,
    }
