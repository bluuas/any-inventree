#!/usr/bin/env python3
"""
Main script for InvenTree operations.
Example usage of the centralized configuration and KiCad plugin class.
"""

import sys
import argparse
import logging
import pandas as pd
from utils.config import Config
from utils.plugin import KiCadPlugin
from utils.error_codes import ErrorCodes
from utils.logging_utils import set_log_level
from utils.units import create_default_units
from utils.entity_resolver import resolve_category_string
from inventree.api import InvenTreeAPI

logger = logging.getLogger('InvenTreeCLI')

def process_configuration_file(api: InvenTreeAPI, kicad: KiCadPlugin, filename: str):
    """
    Process a configuration CSV file to create all necessary part categories based on the CATEGORY hierarchy.
    A Parameter can have references to other columns in the CSV file, for example when choices are defined.
    In this case, the referenced column name is prefixed with a $ sign and the values from that column are inserted as comma-separated choices.
    """
    logger.info(f"Processing configuration file: {filename}")

    import json
    import re
    df = pd.read_csv(filename, dtype=str)
    # process each column seperately: CATEGORY, MANUFACTURER, PARAMETER
    # start with creating the CATEGORIES
    for category in df['CATEGORY'].dropna().unique():
        category_pk, error_code = resolve_category_string(api, category)
        if error_code != ErrorCodes.SUCCESS or category_pk is None:
            logger.error(f"Failed to resolve category for row: {category}")
            return ErrorCodes.CATEGORY_ERROR
        else:
            # if the string ends on "generic" or "critical", add to the KiCad plugin
            if category.endswith("generic"):
                kicad.add_category(category_pk)
            elif category.endswith("critical"):
                kicad.add_category(category_pk)
    return

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

def main():
    parser = argparse.ArgumentParser(description="InvenTree Management CLI")
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--verbose', action='store_true', help='Print configuration details')
    parser.add_argument('--config-file', default='config.csv', help='Path to configuration CSV file')
    
    args = parser.parse_args()
    
    # Set log level
    set_log_level(args.log_level)

    # Validate configuration
    missing_vars = Config.validate_required()
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
        
    # Print configuration for debugging
    if args.verbose:
        Config.print_config()
        
    # Initialize API
    credentials = Config.get_api_credentials()
    api = InvenTreeAPI(credentials['url'], username=credentials['username'], password=credentials['password'])
    
    # Install and configure the KiCad plugin
    plugin = KiCadPlugin(api)
    plugin.install()
    plugin.configure_global_settings()

    process_configuration_file(api, plugin, args.config_file)

    # create physical units
    # create_default_units(api)

if __name__ == "__main__":
    main()