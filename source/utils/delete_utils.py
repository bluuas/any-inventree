"""
Delete utilities for removing all entities from InvenTree.
"""
import logging
from inventree.part import Part
from .entity_resolver import caches

logger = logging.getLogger('InvenTreeCLI')

def delete_all(api):
    """
    Delete all entities from InvenTree.
    """
    logger.info("Starting deletion of all entities from InvenTree")
    
    for entity_type, cache in caches.items():
        try:
            entities = entity_type.list(api)
            logger.info(f"Deleting {len(entities)} instances of {entity_type.__name__}")
            
            for entity in entities:
                try:
                    # Special handling for parts - deactivate first
                    if entity_type == Part:
                        logger.debug(f"Deactivating part: {entity.name} with PK: {entity.pk}")
                        entity.save(data={
                            'active': False,
                            'name': f"{entity.name}",
                            'minimum_stock': 0,
                        }, method='PUT')
                    
                    logger.debug(f"Deleting {entity_type.__name__}: {getattr(entity, 'name', entity.pk)} with PK: {entity.pk}")
                    entity.delete()
                except Exception as e:
                    logger.error(f"Error deleting {entity_type.__name__} with PK {entity.pk}: {e}")
            
            cache.clear()
            logger.info(f"Successfully deleted all {entity_type.__name__} instances")
            
        except Exception as e:
            logger.error(f"Error deleting {entity_type.__name__} instances: {e}")
