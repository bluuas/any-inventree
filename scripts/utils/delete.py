"""
Delete utilities for removing all entities from InvenTree.
"""
import logging
from inventree.part import Part
from .entity_resolver import caches

logger = logging.getLogger('InvenTreeCLI')

def delete_entity_type(api, entity_type_name):
    """
    Delete all instances of a specific entity type from InvenTree.
    
    Args:
        api: InvenTree API instance
        entity_type_name: Name of the entity type to delete (e.g., 'Parameter', 'Part')
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Starting deletion of all {entity_type_name} entities from InvenTree")
    
    # Find the entity type by name
    entity_type = None
    for etype, cache in caches.items():
        if etype.__name__ == entity_type_name:
            entity_type = etype
            break
    
    if entity_type is None:
        logger.error(f"Entity type '{entity_type_name}' not found. Available types: {', '.join([e.__name__ for e in caches.keys()])}")
        return False
    
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
        
        # Clear the cache for this entity type
        caches[entity_type].clear()
        logger.info(f"Successfully deleted all {entity_type.__name__} instances")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting {entity_type.__name__} instances: {e}")
        return False

def delete_all(api):
    """
    Delete all entities from InvenTree.
    """
    logger.info("Starting deletion of all entities from InvenTree")
    
    for entity_type, cache in caches.items():
        delete_entity_type(api, entity_type.__name__)

def list_entity_types():
    """
    List all available entity types that can be deleted.
    
    Returns:
        list: List of entity type names
    """
    return [entity_type.__name__ for entity_type in caches.keys()]
