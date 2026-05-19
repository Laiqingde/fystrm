from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from fystrm.db import get_session
from fystrm.models.media import MediaItem

router = APIRouter(prefix="/api/media", tags=["media"])


class MediaItemOut(BaseModel):
    id: int
    library_id: int
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    tmdb_id: Optional[str] = None
    media_type: str
    source_file_path: str
    source_file_size: int
    strm_path: Optional[str] = None
    nfo_path: Optional[str] = None
    poster_path: Optional[str] = None
    fanart_path: Optional[str] = None
    scrape_status: str
    scrape_error: Optional[str] = None
    created_at: datetime


@router.get("/", response_model=list[MediaItemOut])
async def list_media(
    library_id: int | None = Query(None),
    status: str | None = Query(None),
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
) -> list[MediaItemOut]:
    q = select(MediaItem).order_by(desc(MediaItem.id)).limit(limit)
    if library_id is not None:
        q = q.where(MediaItem.library_id == library_id)
    if status is not None:
        q = q.where(MediaItem.scrape_status == status)
    res = await db.execute(q)
    return [MediaItemOut.model_validate(_serialize(m)) for m in res.scalars().all()]


def _serialize(m: MediaItem) -> dict:
    return {
        "id": m.id, "library_id": m.library_id, "title": m.title,
        "original_title": m.original_title, "year": m.year, "tmdb_id": m.tmdb_id,
        "media_type": m.media_type, "source_file_path": m.source_file_path,
        "source_file_size": m.source_file_size, "strm_path": m.strm_path,
        "nfo_path": m.nfo_path, "poster_path": m.poster_path, "fanart_path": m.fanart_path,
        "scrape_status": m.scrape_status, "scrape_error": m.scrape_error,
        "created_at": m.created_at,
    }
