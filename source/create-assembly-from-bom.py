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

def create_assembly_part(api, name, ipn, revision):
    pcba_category_pk = resolve_entity(api, PartCategory, {'name': 'PCBA', 'parent': None})
    # Create a new part with assembly = True
    assembly_data = {
        'name': name,
        'category': pcba_category_pk,
        'IPN': ipn,
        'revision': revision,
        'assembly': True,
        'component': False
    }

    return resolve_entity(api, Part, assembly_data)

parts_cache = {}
def lookup_mpn_in_parts(api, mpn):
    # return if MPN is None, empty or nan
    if not mpn or pd.isna(mpn):
        logger.info("MPN is empty or None, skipping lookup.")
        return None
    
    # Check cache first
    for part_pk, part in parts_cache.items():
        part_parameters = part['parameters']
        
        # Look for the MPN parameter directly
        for parameter in part_parameters:
            if parameter['template_name'] == "MPN" and parameter['data'] == mpn:
                logger.info(f"Found in cache: MPN: {mpn}, Template Name: MPN, Parameter PK: {parameter['pk']}")
                return parameter['pk']

    # If not found in cache, fetch all parts from the API    
    parts = Part.list(api)

    # Update the cache with fetched parts
    for part in parts:
        part_pk = part['pk']
        part_parameters = part.getParameters()
        
        # Store part and its parameters in the cache
        parts_cache[part_pk] = {
            'name': part['name'],
            'parameters': []
        }
        
        for parameter in part_parameters:
            # Accessing the template_detail name and data using dictionary syntax
            template_name = parameter['template_detail']['name']
            parameter_data = parameter['data']
            parameter_pk = parameter['pk']
            
            # Store parameter in cache
            parts_cache[part_pk]['parameters'].append({
                'data': parameter_data,
                'template_name': template_name,
                'pk': parameter_pk
            })
            
            # Check for matching MPN parameter directly
            if template_name == "MPN" and parameter_data == mpn:
                logger.info(f"Found in API: MPN: {mpn}, Template Name: MPN, Parameter PK: {parameter_pk}")
                return parameter_pk

    logger.info(f"MPN: {mpn} not found in cache or API.")
    return None

def process_bom_file(api, file_path):
    # Load the BOM file into a DataFrame
    bom_df = pd.read_csv(file_path)

    # User input for assembly name and IPN
    assembly_name = input("Enter assembly name (press enter to use the filename): ") or os.path.splitext(os.path.basename(file_path))[0]
    assembly_ipn = input("Enter assembly IPN (leave empty if not applicable): ")
    assembly_revision = input("Enter assembly revision (leave empty if not applicable): ")

    assembly_pk = create_assembly_part(api, assembly_name, assembly_ipn, assembly_revision)

    # Create a DataFrame to store the part and sub-part details
    # response_df = pd.DataFrame(columns=['Part', 'Sub Part', 'Sub Part Detail', 'MPN1', 'MPN2', 'MPN3'])
    response_df = pd.DataFrame(columns=['Assembly PK', 'Sub Part PK', 'MPN1', 'MPN1 PK', 'MPN2', 'MPN2 PK', 'MPN3', 'MPN3 PK'])

    for index, row in bom_df.iterrows():
        # Add each line in the BOM to the assembly, save the "BOM item PK" in the response data
        print(f"Index: {index}, InvenTree PK: {row['InvenTree PK']}")
        item_data = {
            'part': assembly_pk,
            'sub_part': row['InvenTree PK'],
            'quantity': row['Quantity'],
            'validated': True
        }
        response = api.post(url='bom/import/submit/', data={'items': [item_data]})
        # logger.info(response)

        # Check if 'items' exists in the response and is not empty
        if 'items' in response and len(response['items']) > 0:
            item = response['items'][0]
            sub_part_detail = item.get('sub_part_detail', {})
            # Create a temporary DataFrame for the current row
            temp_df = pd.DataFrame([{
                'Assembly PK': item.get('part'),
                'Sub Part PK': item.get('sub_part'),
                # 'Sub Part Detail': sub_part_detail,
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
