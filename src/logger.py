import logging
import sys
from logging.handlers import RotatingFileHandler
from config.settings import LOG_DIR, LOG_LEVEL, ENV

LOG_PATH = LOG_DIR / 'pipelines.log'

def setup_logger(
        name: str = 'bible_pipeline',
        max_bytes: int = 5 * 1024 * 1024,
        backup_count: int = 3,
) -> logging.Logger:
    """
    Configure and return the shared pipeline logger.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.DEBUG)
    
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    # Console: respects LOG_LEVEL from env
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)

    # File: always DEBUG in development, INFO+ in production
    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8',
    )
    file_level = logging.DEBUG if ENV == 'development' else logging.INFO
    file_handler.setLevel(file_level)
    file_handler.setFormatter(fmt)

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger