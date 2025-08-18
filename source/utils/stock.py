import logging
from inventree.api import InvenTreeAPI
from inventree.stock import StockLocation
from .entity_resolver import resolve_entity

logger = logging.getLogger('InvenTreeCLI')

def get_default_stock_location_pk(api: InvenTreeAPI) -> int:
    """
    Create or get the default stock location.
    Returns stock location PK or None on failure.
    """
    try:
        return resolve_entity(api, StockLocation, {
            'name': 'Default',
            'description': 'Default stock location for all parts'
        })
    except Exception as e:
        logger.error(f"Error creating default stock location: {e}")
        return None