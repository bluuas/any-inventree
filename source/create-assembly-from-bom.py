from inventree.api import InvenTreeAPI
from inventree.part import Part, PartCategory
import os
import pandas as pd
from dotenv import load_dotenv
import argparse
import logging
import coloredlogs
from utils.utils import resolve_entity

logger = logging.getLogger(__name__)
coloredlogs.install(logging.INFO)

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
    if not mpn or pd.isna(mpn):
        logger.info("MPN is empty or None, skipping lookup.")
        return None

    # Check cache first
    for part_pk, part in parts_cache.items():
        for parameter in part['parameters']:
            if parameter['template_name'] == "MPN" and parameter['data'] == mpn:
                logger.info(f"Found in cache: MPN: {mpn}, Parameter PK: {parameter['pk']}")
                return parameter['pk']

    # Fetch parts from the API if not found in cache
    parts = Part.list(api)
    update_cache(parts)

    # Check again after updating the cache
    for part in parts:
        for parameter in part.getParameters():
            if parameter['template_detail']['name'] == "MPN" and parameter['data'] == mpn:
                logger.info(f"Found in API: MPN: {mpn}, Parameter PK: {parameter['pk']}")
                return parameter['pk']

    logger.info(f"MPN: {mpn} not found in cache or API.")
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
    response_df = pd.DataFrame(columns=['Assembly PK', 'Sub Part PK', 'MPN1', 'MPN1 PK', 'MPN2', 'MPN2 PK', 'MPN3', 'MPN3 PK'])

    for index, row in bom_df.iterrows():
        logger.info(f"Processing BOM item at index {index}: InvenTree PK: {row['InvenTree PK']}")
        item_data = {
            'part': assembly_pk,
            'sub_part': row['InvenTree PK'],
            'quantity': row['Quantity'],
            'validated': True
        }
        response = api.post(url='bom/import/submit/', data={'items': [item_data]})

        if 'items' in response and response['items']:
            item = response['items'][0]

            # Create a temporary DataFrame for the current row
            temp_df = pd.DataFrame([{
                'Assembly PK': item.get('part'),
                'Sub Part PK': item.get('sub_part'),
                'MPN1': row.get('MPN1'),
                'MPN1 PK': lookup_mpn_in_parts(api, row.get('MPN1')),
                'MPN2': row.get('MPN2'),
                'MPN2 PK': lookup_mpn_in_parts(api, row.get('MPN2')),
                'MPN3': row.get('MPN3'),
                'MPN3 PK': lookup_mpn_in_parts(api, row.get('MPN3')),
            }])
            # Concatenate the temporary DataFrame with the response DataFrame
            response_df = pd.concat([response_df, temp_df], ignore_index=True)
        
    logger.info(f"Response DataFrame: \n{response_df}")

    # Optionally save the DataFrame to a CSV file
    # output_file = os.path.splitext(file_path)[0] + '_response.csv'
    # response_df.to_csv(output_file, index=False)
    # logger.info(f"Response data saved to {output_file}")

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
