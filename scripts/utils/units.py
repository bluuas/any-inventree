import logging
from inventree.api import InvenTreeAPI

from utils.error_codes import ErrorCodes

logger = logging.getLogger(__name__)

def create_unit(api: InvenTreeAPI, name: str,  definition: str, symbol: str):
    """
    Create a custom unit in InvenTree.
    e.g. name='A2S', definition='A ** 2 / t', symbol='A2S'
    definition must be a valid physical unit https://docs.inventree.org/en/stable/concepts/units/
    Returns ErrorCodes.SUCCESS if created successfully, ErrorCodes.FAILURE otherwise.
    """
    unit_data = {
        'definition': definition,
        'name': name,
        'symbol': symbol,
    }
    try:
        response = api.post(url='units/', data=unit_data)
        # Accept both dict (success) and response object (requests)
        if isinstance(response, dict) and response.get('pk'):
            logger.info(f"Created unit: {name} ({symbol})")
            return ErrorCodes.SUCCESS
        if hasattr(response, "status_code") and response.status_code == 201:
            logger.info(f"Created unit: {name} ({symbol})")
            return ErrorCodes.SUCCESS
        logger.error(f"Failed to create unit: {name} ({symbol}) - {getattr(response, 'text', str(response))}")
        return ErrorCodes.ENTITY_CREATION_FAILED
    except Exception as e:
        logger.error(f"Error creating unit: {name} ({symbol}) - {e}")
        return ErrorCodes.ENTITY_CREATION_FAILED

def create_default_units(api: InvenTreeAPI):
    """
    Create a set of default units in InvenTree.
    """
    units = [
        ('A2S', 'A **2 / t', 'A2S'),
        ('AAC', 'A', 'AAC'),
        ('ADC', 'A', 'ADC'),
        ('VAC', 'V', 'VAC'),
        ('VDC', 'V', 'VDC'),
    ]
    for name, definition, symbol in units:
        create_unit(api, name, definition, symbol)