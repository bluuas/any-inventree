# run with python source/create-assembly-from-bom.py -f source/led-flasher-kicad-export.csv

from inventree.api import InvenTreeAPI
from inventree.part import Part, PartCategory, BomItem
import os
import pandas as pd
from dotenv import load_dotenv
import argparse
from utils.utils import resolve_entity

import logging
import coloredlogs
logger = logging.getLogger(__name__)
coloredlogs.install(logging.INFO, logger=logger)

parts_cache = {}

def create_assembly_part(api, name, ipn, revision):
    pcba_category_pk = resolve_entity(api, PartCategory, {'name': 'PCBA', 'parent': None})
    assembly_data = {
        'name': name,
        'category': pcba_category_pk,
        'IPN': ipn,
        'revision': revision,
        'assembly': True,
        'component': False
    }
    return resolve_entity(api, Part, assembly_data)

def lookup_mpn_in_parts(api, mpn):
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

def update_cache(parts):
    for part in parts:
        part_pk = part['pk']
        part_parameters = part.getParameters()
        parts_cache[part_pk] = {
            'name': part['name'],
            'parameters': [{'data': param['data'], 'template_name': param['template_detail']['name'], 'pk': param['pk']} for param in part_parameters]
        }

def process_bom_file(api, file_path):
    bom_df = pd.read_csv(file_path)

    assembly_name = input("Enter assembly name (press enter to use the filename): ") or os.path.splitext(os.path.basename(file_path))[0]
    assembly_ipn = input("Enter assembly IPN (leave empty if not applicable): ")
    assembly_revision = input("Enter assembly revision (leave empty if not applicable): ")

    assembly_pk = create_assembly_part(api, assembly_name, assembly_ipn, assembly_revision)

    # Fetch all BOM substitutes once and store them in a dictionary
    substitutes_response = api.get(url="bom/substitute/")
    existing_substitutes = {(sub['bom_item'], sub['part']): sub['pk'] for sub in substitutes_response}

    # Process each row in the BOM DataFrame
    for index, row in bom_df.iterrows():
        logger.info(f"Processing BOM item at index {index}: InvenTree PK: {row['InvenTree PK']}")
        item_data = {
            'part': assembly_pk,
            'sub_part': row['InvenTree PK'],
            'quantity': row['Quantity'],
            'reference': row['Reference'],
            'validated': 'true'
        }
        bom_item_pk = resolve_entity(api, BomItem, item_data)

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
    
    # validate the assembly BOM after processing all items
    api.patch(url=f"/part/{assembly_pk}/bom-validate/", data={'valid': True})

    logger.info(f"BOM processing completed successfully for file: {file_path}, Named assembly: {assembly_name}, IPN: {assembly_ipn}, Revision: {assembly_revision}")


def main():
    parser = argparse.ArgumentParser(description="BOM parser CLI")
    parser.add_argument('-f', '--file', required=True, help='Path to the BOM file (CSV format)')

    load_dotenv()

    API_URL = os.getenv("INVENTREE_API_URL")
    API_USERNAME = os.getenv("INVENTREE_USERNAME")
    API_PASSWORD = os.getenv("INVENTREE_PASSWORD")

    api = InvenTreeAPI(API_URL, username=API_USERNAME, password=API_PASSWORD)
    args = parser.parse_args()

    # Process the BOM file
    process_bom_file(api, args.file)

if __name__ == "__main__":
    main()
