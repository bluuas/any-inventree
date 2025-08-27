import logging

import coloredlogs

from inventree.api import InvenTreeAPI
from utils.config import Config

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)

def create_unit(api, definition, name, symbol):
    """Create a custom unit in InvenTree."""
    unit_data = {
        'definition': definition,
        'name': name,
        'symbol': symbol,
    }
    response = api.post(url='units/', data=unit_data)
    if response.status_code == 201:
        logger.info(f"Created unit: %s (%s)", name, symbol)
    else:
        logger.error("Failed to create unit: %s (%s) - %s", name, symbol, response.text)

def main():
    credentials = Config.get_api_credentials()
    api = InvenTreeAPI(
        credentials['url'],
        username=credentials['username'],
        password=credentials['password']
    )
    logger.info("Creating units...")
    units = [
        ('A2S', '[A] ** 2 / [t]', 'A2S'),
        ('AAC', '[A]', 'AAC'),
        ('ADC', '[A]', 'ADC'),
        ('VAC', '[V]', 'VAC'),
        ('VDC', '[V]', 'VDC'),
    ]
    for name, definition, symbol in units:
        create_unit(api, definition, name, symbol)

if __name__ == "__main__":
    main()
