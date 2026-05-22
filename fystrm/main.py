from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from fystrm.api import api_router
from fystrm.core.admin_bootstrap import ensure_admin
from fystrm.config import settings
from fystrm.core.logger import setup_logging
from fystrm.core.queue import close_arq_pool

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("fystrm starting | debug={} | port={} | web_dist={}", settings.debug, settings.port, WEB_DIST.exists())
    # 启动自动 alembic upgrade
    try:
        from alembic.config import Config
        from alembic import command
        import asyncio as _aio
        def _migrate():
            cfg = Config("alembic.ini")
            command.upgrade(cfg, "head")
        await _aio.to_thread(_migrate)
        logger.info("alembic upgrade head 完成")
    except Exception as e:
        logger.error("alembic upgrade 失败: {}", e)
    await ensure_admin()
    yield
    await close_arq_pool()
    logger.info("fystrm shutting down")


app = FastAPI(
    title="fystrm",
    description="Open-source media library middleware for CloudDrive2 + Emby",
    version="0.1.0",
    lifespan=lifespan,
)

# API 路由（优先匹配，先注册）
app.include_router(api_router)

# 静态资源（前端 dist）
if WEB_DIST.exists():
    # 静态文件单独挂到 /assets, /favicon 等
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa_fallback(path: str):
        # 不存在的物理文件全部回退到 index.html，让 vue-router 接管
        file_path = WEB_DIST / path
        if path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(WEB_DIST / "index.html")
else:
    @app.get("/")
    async def root() -> dict:
        return {"app": "fystrm", "version": "0.1.0", "docs": "/docs", "web": "not built"}
