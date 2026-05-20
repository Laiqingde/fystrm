from fastapi import APIRouter

from fystrm.api import dashboard, health, library, media, scan, settings_api, transfer, webhooks

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(dashboard.router)
api_router.include_router(library.router)
api_router.include_router(scan.router)
api_router.include_router(media.router)
api_router.include_router(transfer.router)
api_router.include_router(settings_api.router)
api_router.include_router(webhooks.router)
