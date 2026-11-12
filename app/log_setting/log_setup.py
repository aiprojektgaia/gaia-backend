import logging
import logging.handlers
from logging.config import fileConfig

from app.config import get_config


def setup_logs():
    is_local = get_config().DEBUG
    log_file_name = "logging_config"
    if not is_local:
        log_file_name = f"{log_file_name}_info"

    fileConfig(f"app/log_setting/{log_file_name}.ini")
    logger = logging.getLogger()
    logger.info("Logger configured")
