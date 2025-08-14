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
from utils.entity_resolver import resolve_entity, resolve_category_string
from inventree.part import Part, ParameterTemplate
from .relation_utils import resolve_pending_relations
from .error_codes import ErrorCodes

logger = logging.getLogger('csv-processing')
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
        df = pd.read_csv(filename)
        logger.info(f"Processing {df.shape[0]} row(s) from {filename}")
    except Exception as e:
        logger.error(f"Error reading CSV file {filename}: {e}")
        return ErrorCodes.FILE_ERROR
        
    for i, row in df.iterrows():
        if i >= 12:
            break

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
        if error_code != ErrorCodes.SUCCESS:
            logger.error(f"Failed to create part for row {i}: {row['NAME']}")
            return ErrorCodes.PART_CREATION_ERROR

        error_code = create_parameters(api, row, part_pk)
        if error_code != ErrorCodes.SUCCESS:
            logger.warning(f"Failed to create parameters for row {i}: {row['NAME']}")
            
        error_code = create_suppliers_and_manufacturers(api, row, part_pk, get_default_stock_location_pk(api))
        if error_code != ErrorCodes.SUCCESS:
            logger.warning(f"Failed to create suppliers/manufacturers for row {i}: {row['NAME']}")
            
        logger.info(f"Processed row successfully: {row['NAME']}")
        
    # resolve pending relations
    try:
        resolve_pending_relations(api)
    except Exception as e:
        logger.error(f"Error resolving pending relations: {e}")
        return ErrorCodes.RELATIONS_ERROR
        
    return ErrorCodes.SUCCESS

def process_configuration_file(api, filename):
    """
    Process a configuration CSV file to create all necessary part categories based on the CATEGORY hierarchy.
    A Parameter can have references to other columns in the CSV file, for example when choices are defined.
    In this case, the referenced column name is prefixed with a $ sign and the values from that column are inserted as comma-separated choices.
    """
    logger.info(f"Processing configuration file: {filename}")

    import json
    import re
    df = pd.read_csv(filename)
    for idx, row in df.iterrows():
        # Create parameter templates if PARAMETER exists
        if 'PARAMETER' in row and pd.notna(row['PARAMETER']) and str(row['PARAMETER']).strip():
            try:
                param_str = str(row['PARAMETER'])
                # Regex: wrap $WORD with double quotes if not already quoted
                param_str = re.sub(r'(:\s*)\$([A-Za-z0-9_]+)', r'\1"$\2"', param_str)
                param = json.loads(param_str)
                if 'choices' in param and isinstance(param['choices'], str) and param['choices'].startswith('$'):
                    col_name = param['choices'][1:]
                    if col_name in df.columns:
                        choices = df[col_name].dropna().unique()
                        param['choices'] = ', '.join(str(choice) for choice in choices if str(choice).strip())
                    else:
                        param['choices'] = ''
                resolve_entity(api, ParameterTemplate, param)
            except Exception as e:
                logger.error(f"Error processing parameter template at row {idx}: {e}. PARAMETER value: {row['PARAMETER']}")
