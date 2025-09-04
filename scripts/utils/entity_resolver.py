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
from .csv_db_writer import CsvDbWriter

logger = logging.getLogger('InvenTreeCLI')
logger.setLevel(get_configured_level() if callable(get_configured_level) else logging.INFO)

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

writer = CsvDbWriter()

def resolving_complete():
    writer.write_all_db_csv()

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

        # Check cache first
        entity_id = cache.get(composite_key)
        if entity_id is not None:
            logger.debug(f"{entity_type.__name__} '{composite_key}' found in cache with ID: {entity_id}")
            return entity_id

        # Fetch all entities from the API and populate the cache
        try:
            entities = entity_type.list(api)
            entity_dict = {
                tuple(str(getattr(entity, identifier)) for identifier in identifiers): entity.pk 
                for entity in entities
            }
            cache.update(entity_dict)
        except Exception as e:
            logger.error(f"Error fetching {entity_type.__name__} entities from API: {e}")
            return None

        # Check again after updating the cache
        entity_id = cache.get(composite_key)
        if entity_id is not None:
            logger.debug(f"{entity_type.__name__} '{composite_key}' already exists in database with ID: {entity_id}")
            return entity_id
    except Exception as e:
        logger.error(f"Error resolving entity for {entity_type.__name__}: {e}")
        return None
    
    # Create new entity if not found
    try:
        pk = None
        if writer.is_active():
            pk, error = writer.create(api, entity_type, data)
            if error == ErrorCodes.ENTITY_CREATION_FAILED or pk is None:
                logger.warning(f"Writer failed to create {entity_type.__name__} entity '{composite_key}', falling back to API.")
                new_entity = entity_type.create(api, data)
                pk = new_entity.pk
            return pk
        else:
            new_entity = entity_type.create(api, data)
            pk = new_entity.pk
            logger.debug(f"{entity_type.__name__} '{composite_key}' created successfully via API at ID: {pk}")
            cache[composite_key] = pk
            return pk
    except Exception as e:
        logger.error(f"Error creating new {entity_type.__name__} entity '{composite_key}': {e}")
        return None


def clear_entity_caches():
    """
    Clear all entity caches (for use after mass deletion, etc).
    """
    for cache in caches.values():
        cache.clear()
        cache.clear()
