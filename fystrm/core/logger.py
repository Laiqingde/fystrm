import sys
from loguru import logger

from fystrm.config import settings


def setup_logging() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<7}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    # Redis sink: UI 实时日志
    from fystrm.core.log_stream import setup_log_stream
    setup_log_stream()
