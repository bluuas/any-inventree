from inventree.api import InvenTreeAPI
from inventree.part import Part, PartRelated
import os
import pandas as pd
from dotenv import load_dotenv
import argparse
import coloredlogs
import logging
import pprint

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)

def append_substitutes(df, i, MPN, manufacturer_name):
    """
    For every index i (usually inbetween 1, 2 and 3), append the MPN and manufacturer name
    to the DataFrame df. If the DataFrame does not have a column for substitutes,
    create one and append the values.
    If the DataFrame already has a column for substitutes, append the values to that column.
    """
    col_name_mpn = f"MPN{i}"
    col_name_manufacturer = f"Manufacturer{i}"

    if col_name_mpn not in df.columns:
        df[col_name_mpn] = MPN
    else:
        df[col_name_mpn] = df[col_name_mpn].fillna('') + '; ' + MPN

    if col_name_manufacturer not in df.columns:
        df[col_name_manufacturer] = manufacturer_name
    else:
        df[col_name_manufacturer] = df[col_name_manufacturer].fillna('') + '; ' + manufacturer_name

    return df

def process_bom_file(api, file_path):
    # Load the BOM file into a DataFrame
    df = pd.read_csv(file_path)

    logger.debug("\n" + df.head().to_string())

    for index, row in df.iterrows():
        # Resolve the part using the InvenTree API
        part_pk = row['InvenTree PK'] if 'InvenTree PK' in row else None
        if pd.isna(part_pk):
            logger.warning(f"Row {index} does not have a valid InvenTree PK. Skipping.")
            continue

        # Resolve the related part
        try:
            logger.info(f"Resolving part with PK: {part_pk}")
            relations = PartRelated.list(api, part=part_pk)
            logger.debug(f"Found {len(relations)} relations for part PK {part_pk}: {relations}")
            for i, rel in enumerate(relations):
                response = api.get(f"part/related/{rel.pk}/")
                # Extract the PK of the second part
                part_related_pk = response.get('part_2')
                logger.info(f"Related (specific) part PK: {part_related_pk}")
                # get the related part name and Manufacturer part number
                # GET http://inventree.localhost/api/company/part/manufacturer/?search=&offset=0&limit=25&part=1&part_detail=true&manufacturer_detail=true
                response = api.get(url="company/part/manufacturer/", params={
                    'offset': 0,
                    'limit': 25,
                    'part': part_related_pk,
                    'part_detail': False,
                    'manufacturer_detail': True
                })
                # logger.debug("Manufacturer part details:\n" + pprint.pformat(response, indent=2))
                # Extract MPN and manufacturer name from the response
                results = response.get('results', [])
                if results:
                    mpn = results[0].get('MPN', 'Unknown MPN')
                    manufacturer_name = results[0].get('manufacturer_detail', {}).get('name', 'Unknown Manufacturer')
                    logger.info(f"MPN{i}: {mpn}, Manufacturer{i}: {manufacturer_name}")
                    # Append the MPN and manufacturer name to the DataFrame
                    df = append_substitutes(df, i + 1, mpn, manufacturer_name)
                
            return df

        except Exception as e:
            logger.error(f"Error resolving part with PK {part_pk}: {e}")
            continue

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
    df = process_bom_file(api, args.file)
    logger.info("\n" + df.head().to_string())

if __name__ == "__main__":
    main()
