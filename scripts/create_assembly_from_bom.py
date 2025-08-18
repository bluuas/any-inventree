# run with python source/create-assembly-from-bom.py -f source/led-flasher-kicad-export.csv

from inventree.api import InvenTreeAPI
from inventree.part import Part, PartCategory, BomItem
import os
import pandas as pd
import argparse
from .utils.entity_resolver import resolve_entity
from .utils.error_codes import ErrorCodes
from .utils.config import Config

import logging
import coloredlogs
logger = logging.getLogger(__name__)
coloredlogs.install(logging.INFO, logger=logger)

parts_cache = {}

def create_assembly_part(api, name, ipn, revision):
    """
    Create assembly part with error handling.
    Returns (assembly_pk, error_code).
    """
    try:
        pcba_category_pk = resolve_entity(api, PartCategory, {'name': 'PCBA', 'parent': None})
        if not pcba_category_pk:
            logger.error("Failed to create or find PCBA category")
            return None, ErrorCodes.ENTITY_CREATION_FAILED
            
        assembly_data = {
            'name': name,
            'category': pcba_category_pk,
            'IPN': ipn,
            'revision': revision,
            'assembly': True,
            'component': False
        }
        assembly_pk = resolve_entity(api, Part, assembly_data)
        if not assembly_pk:
            logger.error(f"Failed to create assembly part: {name}")
            return None, ErrorCodes.ENTITY_CREATION_FAILED
            
        return assembly_pk, ErrorCodes.SUCCESS
    except Exception as e:
        logger.error(f"Error creating assembly part: {e}")
        return None, ErrorCodes.API_ERROR

def lookup_mpn_in_parts(api, mpn):
    """
    Lookup a part by MPN with error handling.
    Returns part PK or None if not found.
    """
    try:
        if pd.isna(mpn):
            logger.debug("MPN is empty or None, skipping lookup.")
            return None

        # Check cache first, else fetch from the API
        for part_pk, part in parts_cache.items():
            for parameter in part['parameters']:
                if parameter['template_name'] == "MPN" and parameter['data'] == mpn:
                    logger.debug(f"Found in cache: MPN: {mpn}, Parameter PK: {parameter['pk']}, Part PK: {part_pk}")
                    return part_pk

        parts = Part.list(api)
        update_cache(parts)

        # Check again after updating the cache
        for part in parts:
            for parameter in part.getParameters():
                if parameter['template_detail']['name'] == "MPN" and parameter['data'] == mpn:
                    logger.debug(f"Found in API: MPN: {mpn}, Parameter PK: {parameter['pk']}, Part PK: {part['pk']}")
                    return part['pk']

        logger.warning(f"MPN: {mpn} not found in cache or API.")
        return None
    except Exception as e:
        logger.error(f"Error looking up MPN {mpn}: {e}")
        return None

def update_cache(parts):
    """
    Update the parts cache with parameter information.
    """
    for part in parts:
        part_pk = part['pk']
        part_parameters = part.getParameters()
        parts_cache[part_pk] = {
            'name': part['name'],
            'parameters': [{'data': param['data'], 'template_name': param['template_detail']['name'], 'pk': param['pk']} for param in part_parameters]
        }

def process_bom_file(api, file_path):
    """
    Process BOM file and create assembly with error handling.
    Returns error code.
    """
    try:
        bom_df = pd.read_csv(file_path)
        assembly_name = input("Enter assembly name (press enter to use the filename): ") or os.path.splitext(os.path.basename(file_path))[0]
        assembly_ipn = input("Enter assembly IPN (leave empty if not applicable): ")
        assembly_revision = input("Enter assembly revision (leave empty if not applicable): ")

        assembly_pk, error_code = create_assembly_part(api, assembly_name, assembly_ipn, assembly_revision)
        if error_code != ErrorCodes.SUCCESS:
            logger.error(f"Failed to create assembly part with error code: {error_code}")
            return error_code

        # Fetch all BOM substitutes once and store them in a dictionary
        substitutes_response = api.get(url="bom/substitute/")
        existing_substitutes = {(sub['bom_item'], sub['part']): sub['pk'] for sub in substitutes_response}

        # Process each row in the BOM DataFrame
        for index, row in bom_df.iterrows():
            try:
                logger.info(f"Processing BOM item at index {index}: InvenTree PK: {row['InvenTree PK']}")
                item_data = {
                    'part': assembly_pk,
                    'sub_part': row['InvenTree PK'],
                    'quantity': row['Quantity'],
                    'reference': row['Reference'],
                    'validated': 'true'
                }
                bom_item_pk = resolve_entity(api, BomItem, item_data)
                if not bom_item_pk:
                    logger.error(f"Failed to create BOM item for row {index}")
                    continue

                # create BOM substitute for each valid MPN
                for mpn in ['MPN1', 'MPN2', 'MPN3']:
                    mpn_value = row.get(mpn)
                    if pd.notna(mpn_value):
                        mpn_pk = lookup_mpn_in_parts(api, mpn_value)
                        if mpn_pk:
                            # Check if the substitute already exists in the cached substitutes, else create a new one
                            if (bom_item_pk, mpn_pk) in existing_substitutes:
                                logger.debug(f"BOM substitute already exists: BOM Item PK: {bom_item_pk}, Part PK: {mpn_pk}")
                            else:
                                bom_substitute_data = {
                                    'bom_item': bom_item_pk,
                                    'part': mpn_pk,
                                }
                                api.post(url='bom/substitute/', data=bom_substitute_data)
                                logger.debug(f"Created BOM substitute for Part PK: {mpn_pk} with BOM Item PK: {bom_item_pk}")
            except Exception as e:
                logger.error(f"Error processing BOM row {index}: {e}")
                continue
        
        # validate the assembly BOM after processing all items
        try:
            api.patch(url=f"/part/{assembly_pk}/bom-validate/", data={'valid': True})
        except Exception as e:
            logger.error(f"Failed to validate assembly BOM: {e}")
            return ErrorCodes.API_ERROR

        logger.info(f"BOM processing completed successfully for file: {file_path}, Named assembly: {assembly_name}, IPN: {assembly_ipn}, Revision: {assembly_revision}")
        return ErrorCodes.SUCCESS
        
    except Exception as e:
        logger.error(f"Error processing BOM file {file_path}: {e}")
        return ErrorCodes.BOM_PROCESSING_ERROR


def main():
    parser = argparse.ArgumentParser(description="BOM parser CLI")
    parser.add_argument('-f', '--file', required=True, help='Path to the BOM file (CSV format)')

    try:
        # Validate required configuration
        missing_vars = Config.validate_required()
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            return ErrorCodes.INVALID_ASSEMBLY_DATA

        credentials = Config.get_api_credentials()
        api = InvenTreeAPI(credentials['url'], username=credentials['username'], password=credentials['password'])
        args = parser.parse_args()

        # Process the BOM file
        error_code = process_bom_file(api, args.file)
        if error_code != ErrorCodes.SUCCESS:
            logger.error(f"Failed to process BOM file with error code: {error_code}")
            return error_code
            
        return ErrorCodes.SUCCESS
        
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        return ErrorCodes.API_ERROR

if __name__ == "__main__":
    main()
