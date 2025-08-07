"""
CSV file processing logic for importing data into InvenTree.
"""
import logging
import pandas as pd
from .part_creation import (
    create_parameters,
    create_suppliers_and_manufacturers
)
from .stock import get_default_stock_location_pk
from utils.entity_resolver import resolve_entity, resolve_category_string
from inventree.part import Part, ParameterTemplate

logger = logging.getLogger('InvenTreeCLI')

# Example: site_url can be passed as an argument or set globally
SITE_URL = None

def process_database_file(api, filename, site_url=None):
    """
    Process a CSV file and create parts, parameters, suppliers, etc.
    Assumes categories are already created from configuration.
    """
    try:
        df = pd.read_csv(filename)
        logger.info(f"Processing {df.shape[0]} row(s) from {filename}")
        for i, row in df.iterrows():
            if i > 20:
                break

            category_string = f"{row['CATEGORY']} / {row['TYPE']}"
            if pd.isna(category_string):
                logger.error(f"Row {i} has an error in CATEGORY. Exiting.")
                quit()
            category_pk = resolve_category_string(api, category_string)
            if category_pk is None:
                logger.error(f"Failed to resolve category for row {i}: {row['CATEGORY']}")
                quit()

            part_pk = resolve_entity(api, Part, {
                'name': row['NAME'],
                'category': category_pk,
                'description': row['DESCRIPTION'] if not pd.isna(row['DESCRIPTION']) else '',
                'revision': row['REVISION'] if not pd.isna(row['REVISION']) else '0',
            })

            # create_parameters(api, row, part_generic_pk, part_specific_pks)
            # create_suppliers_and_manufacturers(api, row, part_specific_pks, stock_location_pk)
            logger.info(f"Processed row successfully: {row['NAME']}")
    except Exception as e:
        logger.error(f"Error processing '{filename}': {e}")

def process_configuration_file(api, filename):
    """
    Process a configuration CSV file to create all necessary part categories based on the CATEGORY hierarchy.
    """
    logger.info(f"Processing configuration file: {filename}")
    import json
    import re
    df = pd.read_csv(filename)
    for idx, row in df.iterrows():
        # Create categories if CATEGORY exists
        if 'CATEGORY' in row and pd.notna(row['CATEGORY']):
            resolve_category_string(api, row['CATEGORY'])
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
