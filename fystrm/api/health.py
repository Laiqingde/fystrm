from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/api/version")
async def version() -> dict:
    return {"name": "fystrm", "version": "0.1.0"}
