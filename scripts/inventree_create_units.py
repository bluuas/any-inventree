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
    try:
        response = api.post(url='units/', data=unit_data)
        logger.info(f"Response: {response}")
    except Exception as e:
        logger.error(f"Error creating unit: {name} ({symbol}) - {e}")

def main():
    credentials = Config.get_api_credentials()
    api = InvenTreeAPI(
        credentials['url'],
        username=credentials['username'],
        password=credentials['password']
    )
    logger.info("Creating units...")
    units = [
        ('A ** 2 / t', 'A2S', 'A2S'),
        ('A', 'AAC', 'AAC'),
        ('A', 'ADC', 'ADC'),
        ('V', 'VAC', 'VAC'),
        ('V', 'VDC', 'VDC'),
    ]
    for definition, name, symbol in units:
        create_unit(api, definition, name, symbol)

if __name__ == "__main__":
    main()
