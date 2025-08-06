"""
Entity resolution and caching utilities for InvenTree entities.
"""
import logging
from inventree.api import InvenTreeAPI
from inventree.base import Attachment
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part, Parameter, ParameterTemplate, PartRelated, BomItem
from inventree.stock import StockItem, StockLocation

logger = logging.getLogger('InvenTreeCLI')

# Caches for entities to speed up lookups
caches = {
    Attachment: {},
    BomItem: {},
    Company: {},
    ManufacturerPart: {},
    Parameter: {},
    ParameterTemplate: {},
    Part: {},
    PartCategory: {},
    PartRelated: {},
    StockItem: {},
    StockLocation: {},
    SupplierPart: {},
}

# Lookup Table for identifiers per entity type
IDENTIFIER_LUT = {
    Attachment: ['filename', 'model_id'],
    BomItem: ['part', 'sub_part'],
    Company: ['name'],
    ManufacturerPart: ['MPN'],
    Parameter: ['part', 'template'],
    ParameterTemplate: ['name'],
    Part: ['name', 'category'],
    PartCategory: ['name', 'parent'],
    PartRelated: ['part_1', 'part_2'],
    StockItem: ['part', 'supplier_part'],
    StockLocation: ['name'],
    SupplierPart: ['SKU'],
}

def resolve_entity(api: InvenTreeAPI, entity_type, data):
    """
    Resolve (find or create) an entity of the given type using identifier fields.
    Uses a cache to avoid redundant API calls.
    """
    identifiers = IDENTIFIER_LUT.get(entity_type, [])
    if not identifiers:
        logger.error(f"No identifiers found for entity type: {entity_type.__name__}")
        return None

    try:
        cache = caches[entity_type]
        composite_key = tuple(data[identifier] for identifier in identifiers if identifier in data)

        # Check cache first
        entity_id = cache.get(composite_key)
        if entity_id is not None:
            logger.debug(f"{entity_type.__name__} '{composite_key}' found in cache with ID: {entity_id}")
            return entity_id

        # Fetch all entities from the API and populate the cache
        entity_dict = {tuple(getattr(entity, identifier) for identifier in identifiers): entity.pk for entity in entity_type.list(api)}
        cache.update(entity_dict)

        # Check again after updating the cache
        entity_id = cache.get(composite_key)
        if entity_id is not None:
            logger.debug(f"{entity_type.__name__} '{composite_key}' already exists in database with ID: {entity_id}")
            return entity_id

        # Create new entity if not found
        new_entity = entity_type.create(api, data)
        logger.debug(f"{entity_type.__name__} '{composite_key}' created successfully at ID: {new_entity.pk}")
        cache[composite_key] = new_entity.pk
        return new_entity.pk

    except Exception as e:
        logger.error(f"Error resolving entity for {entity_type.__name__} '{composite_key}': {e}")
        return None

def clear_entity_caches():
    """
    Clear all entity caches (for use after mass deletion, etc).
    """
    for cache in caches.values():
        cache.clear()
