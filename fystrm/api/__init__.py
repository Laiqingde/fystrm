from fastapi import APIRouter, Depends

from fystrm.api import auth, dashboard, health, library, logs, media, scan, settings_api, transfer, webhooks
from fystrm.api.auth import get_current_user

api_router = APIRouter()

# 公开路由 (不需要登录)
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(webhooks.router)  # 用 Bearer token 自己鉴权

# 受保护路由 (需要 JWT)
protected = [dashboard, library, scan, media, transfer, settings_api, logs]
for mod in protected:
    api_router.include_router(mod.router, dependencies=[Depends(get_current_user)])
