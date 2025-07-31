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


def process_bom_file(api, file_path):
    # Load the BOM file into a DataFrame
    bom_df = pd.read_csv(file_path)

    # User input for assembly name and IPN
    assembly_name = input("Enter assembly name (press enter to use the filename): ") or os.path.splitext(os.path.basename(file_path))[0]
    assembly_ipn = input("Enter assembly IPN (leave empty if not applicable): ")
    assembly_revision = input("Enter assembly revision (leave empty if not applicable): ")

    assembly_pk = create_assembly_part(api, assembly_name, assembly_ipn, assembly_revision)

    for index, row in bom_df.iterrows():
        print(f"Index: {index}, InvenTree PK: {row['InvenTree PK']}")
        item_data = {
            'part': assembly_pk,
            'sub_part': row['InvenTree PK'],
            'quantity': row['Quantity']
        }
        response = api.post(url='bom/import/submit/', data={'items': [item_data]})
        logger.info(response)

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
