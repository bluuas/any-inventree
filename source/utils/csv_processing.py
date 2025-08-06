"""
CSV file processing logic for importing data into InvenTree.
"""
import logging
import pandas as pd
from .part_creation import (
    create_default_stock_location,
    create_generic_part,
    create_specific_parts,
    create_parameters,
    create_suppliers_and_manufacturers
)
from .category import create_categories
from utils.entity_resolver import resolve_entity
from inventree.part import PartCategory

logger = logging.getLogger('InvenTreeCLI')

# Example: site_url can be passed as an argument or set globally
SITE_URL = None

def process_csv_file(api, filename, site_url=None):
    """
    Process a CSV file and create parts, parameters, suppliers, etc.
    Assumes categories are already created from configuration.
    """
    try:
        df = pd.read_csv(filename).iloc[1:]  # Drop the 2nd row with the Units
        logger.info(f"Processing {df.shape[0]} row(s) from {filename}")
        for i, row in df.iterrows():
            if i > 20:
                break
            stock_location_pk = create_default_stock_location(api)
            # Look up the lowest-level category (assume last in CATEGORY split)
            category_levels = [level.strip() for level in str(row['CATEGORY']).split('/') if level and str(level).lower() != 'nan']
            if not category_levels:
                logger.warning(f"No valid category for row: {row}")
                continue
            # Find the lowest-level category PK
            parent_pk = None
            for level in category_levels:
                parent_pk = resolve_entity(api, PartCategory, {'name': level, 'parent': parent_pk, 'structural': True})
            # Use the 'generic' and 'specific' subcategories under the lowest-level
            generic_pk = resolve_entity(api, PartCategory, {'name': 'generic', 'parent': parent_pk})
            specific_pk = resolve_entity(api, PartCategory, {'name': 'specific', 'parent': parent_pk})
            part_generic_pk = create_generic_part(api, row, generic_pk, site_url)
            part_specific_pks = create_specific_parts(api, row, part_generic_pk, specific_pk)
            create_parameters(api, row, part_generic_pk, part_specific_pks)
            create_suppliers_and_manufacturers(api, row, part_specific_pks, stock_location_pk)
            logger.info(f"Processed row successfully: {row['NAME']}")
    except Exception as e:
        logger.error(f"Error processing '{filename}': {e}")

def process_configuration_file(api, filename):
    """
    Process a configuration CSV file to create all necessary part categories based on the CATEGORY hierarchy.
    """
    logger.info(f"Processing configuration file: {filename}")
    df = pd.read_csv(filename)
    for idx, row in df.iterrows():
        # Split the CATEGORY field by ' / ' to get the hierarchy
        category_levels = [level.strip() for level in str(row['CATEGORY']).split('/') if level and str(level).lower() != 'nan']
        if not category_levels:
            continue
        create_categories(api, category_levels)
