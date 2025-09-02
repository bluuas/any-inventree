"""
Entity resolution and caching utilities for InvenTree entities.
"""

import logging
from utils.logging_utils import get_configured_level
from inventree.api import InvenTreeAPI
from inventree.base import Attachment
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part, Parameter, ParameterTemplate, PartRelated, BomItem
from inventree.stock import StockItem, StockLocation
from .error_codes import ErrorCodes
from collections import OrderedDict

logger = logging.getLogger('InvenTreeCLI')
logger.setLevel(get_configured_level() if callable(get_configured_level) else logging.INFO)

MAX_CACHE_SIZE = 100  # Adjust as needed

# Use OrderedDict for LRU behavior
caches = {
    Attachment: OrderedDict(),
    BomItem: OrderedDict(),
    Company: OrderedDict(),
    ManufacturerPart: OrderedDict(),
    Parameter: OrderedDict(),
    ParameterTemplate: OrderedDict(),
    Part: OrderedDict(),
    PartCategory: OrderedDict(),
    PartRelated: OrderedDict(),
    StockItem: OrderedDict(),
    StockLocation: OrderedDict(),
    SupplierPart: OrderedDict(),
}

# Lookup Table for identifiers per entity type
IDENTIFIER_LUT = {
    Attachment: ['link', 'model_id'],
    BomItem: ['part', 'sub_part'],
    Company: ['name'],
    ManufacturerPart: ['MPN'],
    Parameter: ['part', 'template'],
    ParameterTemplate: ['name'],
    Part: ['name', 'category', 'revision'],
    PartCategory: ['name', 'parent'],
    PartRelated: ['part_1', 'part_2'],
    StockItem: ['part', 'supplier_part'],
    StockLocation: ['name'],
    SupplierPart: ['SKU'],
}

def resolve_category_string(api: InvenTreeAPI, category_string: str) -> tuple:
    """
    Resolve a category string (e.g. 'Passive Component / Resistor / Metal thickfilm / generic ')
    into the lowest-level category PK.
    Create all not yet existing categories.
    Ensures each category is created with the correct parent.
    The lowest category level will have structural=False.
    Returns (category_pk, error_code).
    """
    try:
        category_levels = [level.strip() for level in category_string.split('/') if level and str(level).lower() != 'nan']
        if not category_levels:
            logger.error(f"No valid category levels found in string: {category_string}")
            return None, ErrorCodes.INVALID_DATA

        parent_pk = None
        for idx, level in enumerate(category_levels):
            is_last = idx == len(category_levels) - 1
            data = {'name': level, 'structural': not is_last, 'parent': parent_pk}
            parent_pk = resolve_entity(api, PartCategory, data)
            if parent_pk is None:
                logger.error(f"Failed to create/resolve category: {level}")
                return None, ErrorCodes.ENTITY_CREATION_FAILED

        return parent_pk, ErrorCodes.SUCCESS
    except Exception as e:
        logger.error(f"Error resolving category string '{category_string}': {e}")
        return None, ErrorCodes.API_ERROR

def _cache_set(cache, key, value):
    cache[key] = value
    if len(cache) > MAX_CACHE_SIZE:
        # Remove the oldest half of the cache
        num_to_remove = len(cache) // 2
        for _ in range(num_to_remove):
            cache.popitem(last=False)  # Remove oldest

def resolve_entity(api: InvenTreeAPI, entity_type, data):
    """
    Resolve an entity by checking cache first, then API, then creating if needed.
    Returns entity PK or None on failure.
    """
    identifiers = IDENTIFIER_LUT.get(entity_type, [])
    if not identifiers:
        logger.error(f"No identifiers found for entity type: {entity_type.__name__}")
        return None

    try:
        cache = caches[entity_type]
        composite_key = tuple(str(data[identifier]) for identifier in identifiers if identifier in data)

        entity_id = cache.get(composite_key)
        if entity_id is not None:
            cache.move_to_end(composite_key)  # Mark as recently used
            logger.debug(f"{entity_type.__name__} '{composite_key}' found in cache with ID: {entity_id}")
            return entity_id

        # Fetch all entities from the API and populate the cache
        try:
            entities = entity_type.list(api)
            for entity in entities:
                key = tuple(str(getattr(entity, identifier)) for identifier in identifiers)
                _cache_set(cache, key, entity.pk)
        except Exception as e:
            logger.error(f"Error fetching {entity_type.__name__} entities from API: {e}")
            return None

        # Check again after updating the cache
        entity_id = cache.get(composite_key)
        if entity_id is not None:
            logger.debug(f"{entity_type.__name__} '{composite_key}' already exists in database with ID: {entity_id}")
            return entity_id

        # Create new entity if not found
        try:
            new_entity = entity_type.create(api, data)
            logger.debug(f"{entity_type.__name__} '{composite_key}' created successfully at ID: {new_entity.pk}")
            _cache_set(cache, composite_key, new_entity.pk)
            return new_entity.pk
        except Exception as e:
            logger.error(f"Error creating new {entity_type.__name__} entity '{composite_key}': {e}")
            return None

    except Exception as e:
        logger.error(f"Error resolving entity for {entity_type.__name__}: {e}")
        return None

def clear_entity_caches():
    """
    Clear all entity caches (for use after mass deletion, etc).
    """
    for cache in caches.values():
        cache.clear()
