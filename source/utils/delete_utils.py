"""
Delete utilities for removing all entities from InvenTree.
"""
import logging
from inventree.part import Part
from .entity_resolver import caches

logger = logging.getLogger('InvenTreeCLI')

def delete_all(api):
    """
    Delete all parts and cached entities from InvenTree.
    """
    parts = Part.list(api)
    logger.info(f"Deleting {len(parts)} parts")
    for part in parts:
        try:
            logger.debug(f"Deactivating part: {part.name} with PK: {part.pk}")
            part.save(data={
                'active': False,
                'name': f"{part.name}",
                'minimum_stock': 0,
            }, method='PUT')
            logger.debug(f"Deleting part: {part.name} with PK: {part.pk}")
            part.delete()
        except Exception as e:
            logger.error(f"Error processing part '{part.name}': {e}")
    for entity_type, cache in caches.items():
        try:
            entities = entity_type.list(api)
            logger.debug(f"Deleting {len(entities)} instances of {entity_type.__name__}")
            for entity in entities:
                entity.delete()
            cache.clear()
        except Exception as e:
            logger.error(f"Error deleting {entity_type.__name__} instances: {e}")
