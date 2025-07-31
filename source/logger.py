import logging
import coloredlogs

def setup_logger(name: str) -> logging.Logger:
    """Set up a logger with a specific name."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Set the logging level

    # Create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(ch)

    # Optional: Use coloredlogs for better visibility in the console
    coloredlogs.install(level='DEBUG', logger=logger)

    return logger
