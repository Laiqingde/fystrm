from arq.connections import RedisSettings
from loguru import logger

from fystrm.config import settings
from fystrm.core.logger import setup_logging


async def ping(ctx: dict) -> str:
    """占位任务，Stage 5 会被真实 task 取代。"""
    logger.info("ping task invoked")
    return "pong"


async def startup(ctx: dict) -> None:
    setup_logging()
    logger.info("arq worker started")


async def shutdown(ctx: dict) -> None:
    logger.info("arq worker stopped")


class WorkerSettings:
    redis_settings = RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
        database=settings.redis_db,
    )
    functions = [ping]
    on_startup = startup
    on_shutdown = shutdown
