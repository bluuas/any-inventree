"""
Logging setup and log level management utilities.
"""
import logging
import coloredlogs

logger = logging.getLogger('InvenTreeCLI')
logger.propagate = False  # Prevent log message duplication

# Only install coloredlogs if no handlers are present
if not logger.hasHandlers():
    coloredlogs.install(logging.INFO, logger=logger)

def set_log_level(level: str):
    """
    Set the log level for the logger and coloredlogs.
    """
    try:
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(log_level)
        coloredlogs.set_level(level=log_level)
    except AttributeError:
        logger.error(f"Invalid log level: {level}. Defaulting to INFO.")
        logger.setLevel(logging.INFO)
        coloredlogs.set_level(level=logging.INFO)

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("inventree").setLevel(logging.WARNING)
