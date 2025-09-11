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
from .csv_db_writer import csv_db_writer
from .cache import entity_cache

logger = logging.getLogger('InvenTreeCLI')
logger.setLevel(get_configured_level() if callable(get_configured_level) else logging.INFO)

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
    Resolve an entity by checking cache first, then API (once), then creating if needed.
    Returns entity PK or None on failure.
    """
    try:
        # 1. try to find in cache
        pk = entity_cache.find_by_identifiers(entity_type, data)
        if pk is not None:
            return pk
        else:
            logger.debug(f"{entity_type.__name__} not found in local cache")

        # 2. not found in cache, try to find it in the csv_db_writer (if active)
        if csv_db_writer.is_active():
            try:
                pk = csv_db_writer.find_by_identifiers(entity_type, data)
                if pk is not None:
                    return pk
                else:
                    logger.debug(f"{entity_type.__name__} not found in csv_db_writer table")
            except Exception as e:
                logger.error(f"Error searching csv_db_writer for {entity_type.__name__}: {e}")
                return None
            
        # 3. not found in cache or csv_db_writer, try to create it via csv_db_writer (if active)
        if csv_db_writer.is_active():
            pk, error = csv_db_writer.create(api, entity_type, data)
            # Add to cache
            if error == ErrorCodes.SUCCESS:
                entity_cache.add(entity_type, pk, data.copy())
                logger.debug(f"{entity_type.__name__} '{data}' created successfully via csv_db_writer at ID: {pk}")
                return pk
            elif error == ErrorCodes.ENTITY_CREATION_FAILED:
                pass  # try to create via API below
            else:
                logger.error(f"Error creating {entity_type.__name__} via csv_db_writer: {error}")
                return None

        # 4. not found in cache, csv_db_writer inactive, add it via API
        try:
            new_entity = entity_type.create(api, data)
            pk = new_entity.pk
            logger.debug(f"{entity_type.__name__} '{data}' created successfully via InvenTree API at ID: {pk}")
            entity_cache.add(entity_type, pk, data.copy())
            return pk
        except Exception as e:
            logger.error(f"Error creating new {entity_type.__name__}: {e}")
            return None

    except Exception as e:
        logger.error(f"Error resolving entity for {entity_type.__name__}: {e}")
        return None