import logging
import sys
from logging.handlers import RotatingFileHandler
from config.settings import LOG_DIR, ENV

LOG_DIR.mkdir(parents=True, exist_ok=True)
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
    
    level = logging.DEBUG if ENV == 'development' else logging.INFO
    
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    # Console: always INFO
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
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger