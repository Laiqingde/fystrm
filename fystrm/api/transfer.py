from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/transfer", tags=["transfer"])


class TransferRequest(BaseModel):
    share_url: str
    share_password: str | None = None
    target_drive_account_id: int | None = None
    target_path: str | None = None


@router.post("/")
async def start_transfer(_: TransferRequest) -> dict:
    """转存接口预留。v0.1 未实现，v0.2+ 接入真实网盘 API。"""
    raise HTTPException(
        status_code=501,
        detail={
            "error": "not_implemented",
            "message": "Transfer feature is reserved for v0.2+. Currently only directory scanning is supported.",
            "version": "0.1.0",
        },
    )
