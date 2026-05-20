from arq.connections import RedisSettings
from loguru import logger

from fystrm.config import settings
from fystrm.core.logger import setup_logging
from fystrm.tasks.scan import scan_library_task
from fystrm.tasks.webhook import handle_file_event


async def ping(ctx: dict) -> str:
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
    functions = [ping, scan_library_task, handle_file_event]
    on_startup = startup
    on_shutdown = shutdown
    job_timeout = 1800  # 30min, 大目录扫描留时间
    max_jobs = 4
