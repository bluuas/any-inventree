from inventree.api import InvenTreeAPI
import os
import pandas as pd
from dotenv import load_dotenv
import argparse
import coloredlogs
import logging

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)

def process_bom_file(file_path, parts, parameters):
    # Load the BOM file into a DataFrame
    bom_df = pd.read_csv(file_path)

    # Create a new column 'InvenTree PK' initialized with None
    bom_df.insert(0, 'InvenTree PK', None)

    # Create a mapping of MPN to InvenTree PK using parameters
    mpn_to_part_pk = {}
    for param in parameters:
        if param['template_detail']['name'] == 'MPN':
            part_pk = param['part']
            mpn_value = param['data']
            mpn_to_part_pk[mpn_value] = part_pk

    # Match MPNs and populate the 'InvenTree PK' column
    for index, row in bom_df.iterrows():
        mpn = row.get('MPN')  # Assuming the MPN column is named 'MPN'
        if mpn in mpn_to_part_pk:
            bom_df.at[index, 'InvenTree PK'] = mpn_to_part_pk[mpn]

    # Save the processed BOM file with a "_processed" suffix
    processed_file_path = os.path.splitext(file_path)[0] + "_processed.csv"
    bom_df.to_csv(processed_file_path, index=False)
    logger.info(f"Processed BOM saved to {processed_file_path}")

    # Log the head of the DataFrame
    logger.info("Head of the processed BOM:")
    logger.info("\n" + bom_df.head().to_string(index=False))

def main():
    parser = argparse.ArgumentParser(description="BOM parser CLI")
    parser.add_argument('-f', '--file', required=True, help='Path to the BOM file (CSV format)')

    load_dotenv()

    API_URL = os.getenv("INVENTREE_API_URL")
    API_USERNAME = os.getenv("INVENTREE_USERNAME")
    API_PASSWORD = os.getenv("INVENTREE_PASSWORD")

    api = InvenTreeAPI(API_URL, username=API_USERNAME, password=API_PASSWORD)
    args = parser.parse_args()

    # Fetch parts from the API
    parts = api.get(url='part')
    parameters = api.get(url='part/parameter/', search='MPN')
    logger.debug(parameters[0])  # Log the first parameter for debugging

    # Process the BOM file
    process_bom_file(args.file, parts, parameters)

if __name__ == "__main__":
    main()
