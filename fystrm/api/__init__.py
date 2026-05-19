from fastapi import APIRouter

from fystrm.api import health

api_router = APIRouter()
api_router.include_router(health.router)
