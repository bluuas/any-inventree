"""
Logging setup and log level management utilities.
"""
import logging
import coloredlogs

logger = logging.getLogger('InvenTreeCLI')

# Set up coloredlogs for the logger
coloredlogs.install(logging.INFO, logger=logger)


def set_log_level(level: str):
    """
    Set the log level for the logger and coloredlogs.
    """
    try:
        log_level = getattr(logging, level.upper(), logging.INFO)
        coloredlogs.set_level(level=log_level)
    except AttributeError:
        logger.error(f"Invalid log level: {level}. Defaulting to INFO.")
        coloredlogs.set_level(level=logging.INFO)
