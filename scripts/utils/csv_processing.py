"""
CSV file processing logic for importing data into InvenTree.
"""
import logging
from utils.logging_utils import get_configured_level
import pandas as pd

from utils.plugin import KiCadPlugin
from .part_creation import (
    create_part,
    create_parameters,
    create_suppliers_and_manufacturers,
)
from .stock import get_default_stock_location_pk
from utils.entity_resolver import resolve_entity, resolve_category_string, resolving_complete
from inventree.part import Part, ParameterTemplate
from .relation_utils import resolve_pending_relations
from .error_codes import ErrorCodes

logger = logging.getLogger('InvenTreeCLI')
logger.setLevel(get_configured_level() if callable(get_configured_level) else logging.INFO)

def process_database_file(api, filename):
    """
    Process a CSV file and create parts, parameters, suppliers, etc.
    Assumes categories are already created from configuration.
    Returns error code.
    """
    # Initialize KiCad plugin for category management
    kicad_plugin = KiCadPlugin(api)

    try:
        # Ensure all columns are read as strings to prevent e.g. "0402" being interpreted as 402
        df = pd.read_csv(filename, dtype=str)
        logger.info(f"Processing {df.shape[0]} row(s) from {filename}")
    except Exception as e:
        logger.error(f"Error reading CSV file {filename}: {e}")
        return ErrorCodes.FILE_ERROR

    for i, row in df.iloc[:].iterrows():
        error_code = None
        # --------------------------------- category --------------------------------- #
        category_string = f"{row['CATEGORY']} / {row['TYPE']}"
        if pd.isna(category_string):
            logger.error(f"Row {i} has an error in CATEGORY. Exiting.")
            return ErrorCodes.CATEGORY_ERROR
            
        category_pk, error_code = resolve_category_string(api, category_string)
        if error_code != ErrorCodes.SUCCESS or category_pk is None:
            logger.error(f"Failed to resolve category for row {i}: {row['CATEGORY']}")
            return ErrorCodes.CATEGORY_ERROR
            
        if row['TYPE'] in ['generic', 'critical']:
            # Add the generic or critical category to the KiCad plugin
            kicad_plugin.add_category(category_pk)
            
        # ----------------------------------- part ----------------------------------- #
        part_pk, error_code = create_part(api, row, category_pk)
        if error_code == ErrorCodes.INVALID_NAME:
            logger.warning(f"Skipping row {i} due to invalid or missing part name.")
        elif error_code != ErrorCodes.SUCCESS:
            logger.error(f"Failed to create part for row {i}: {row['NAME']}")
            continue

        error_code = create_parameters(api, row, part_pk)
        error_code = create_suppliers_and_manufacturers(api, row, part_pk, get_default_stock_location_pk(api))

        if error_code == ErrorCodes.SUCCESS:
            logger.info(f"Processed row {row.name} successfully: {row['NAME']}")
        else:
            logger.error(f"Error processing row {row.name}: {row['NAME']} (Error code: {error_code})")
            
        
    # resolve pending relations
    try:
        resolve_pending_relations(api)
    except Exception as e:
        logger.error(f"Error resolving pending relations: {e}")
        return ErrorCodes.RELATIONS_ERROR
        
    # Write all buffered part rows to DB CSV using pandas
    try:
        resolving_complete()
    except Exception as e:
        logger.error(f"Error writing parts DataFrame to DB CSV: {e}")

    return ErrorCodes.SUCCESS