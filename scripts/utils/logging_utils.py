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

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("inventree").setLevel(logging.WARNING)

def set_log_level(level: str):
    """
    Set the log level for the logger and coloredlogs.
    """
    try:
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(log_level)
        
        # Clear existing handlers to prevent duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Install coloredlogs with the correct level
        coloredlogs.install(log_level, logger=logger)
        logger.info(f"Log level set to {level.upper()}")
    except AttributeError:
        logger.error(f"Invalid log level: {level}. Defaulting to INFO.")
        logger.setLevel(logging.INFO)
        # Clear existing handlers to prevent duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        coloredlogs.install(logging.INFO, logger=logger)

def get_configured_level() -> int:
    """
    Get the current log level configured for the InvenTreeCLI logger.
    Returns:
        int: The current log level (e.g., logging.INFO, logging.WARNING).
    """
    return logger.level
