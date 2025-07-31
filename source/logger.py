import logging
import coloredlogs

def setup_logging(level: str) -> None:
    """Set up logging configuration."""
    logging.basicConfig(level=level,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    coloredlogs.install(level=level)

    # Disable logging for specific modules
    logging.getLogger('inventree').setLevel(logging.WARNING)  # Suppress requests logging
