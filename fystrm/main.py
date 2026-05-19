from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from fystrm.api import api_router
from fystrm.config import settings
from fystrm.core.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("fystrm starting up | debug={} | port={}", settings.debug, settings.port)
    yield
    logger.info("fystrm shutting down")


app = FastAPI(
    title="fystrm",
    description="Open-source media library middleware for CloudDrive2 + Emby",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/")
async def root() -> dict:
    return {"app": "fystrm", "version": "0.1.0", "docs": "/docs"}
