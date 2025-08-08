from inventree.api import InvenTreeAPI
from inventree.part import PartRelated
import os
import argparse
import logging
import pprint
import pandas as pd
from dotenv import load_dotenv
import coloredlogs

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)

def append_substitutes(row, i, manufacturer_name, mpn):
    """
    Update a row with MPN and manufacturer name for the i-th substitute.
    """
    row[f"Manufacturer{i}"] = manufacturer_name
    row[f"MPN{i}"] = mpn
    return row

def process_bom_file(api, file_path):
    df = pd.read_csv(file_path)
    logger.debug("\n" + df.head().to_string())

    # Prepare columns for up to 3 substitutes
    for i in range(1, 4):
        df[f"Manufacturer{i}"] = None
        df[f"MPN{i}"] = None

    updated_rows = []
    for index, row in df.iterrows():
        part_pk = row.get('InvenTree PK')
        if pd.isna(part_pk):
            logger.warning(f"Row {index} does not have a valid InvenTree PK. Skipping.")
            updated_rows.append(row)
            continue
        try:
            logger.info(f"Resolving part with PK: {part_pk}")
            relations = PartRelated.list(api, part=part_pk)
            logger.debug(f"Found {len(relations)} relations for part PK {part_pk}: {relations}")
            for i, rel in enumerate(relations[:3]):  # Only up to 3 substitutes
                rel_response = api.get(f"part/related/{rel.pk}/")
                part_related_pk = rel_response.get('part_2')
                logger.info(f"Related (specific) part PK: {part_related_pk}")
                manuf_response = api.get(url="company/part/manufacturer/", params={
                    'offset': 0,
                    'limit': 1,
                    'part': part_related_pk,
                    'part_detail': False,
                    'manufacturer_detail': True
                })
                results = manuf_response.get('results', [])
                if results:
                    mpn = results[0].get('MPN', 'Unknown MPN')
                    manufacturer_name = results[0].get('manufacturer_detail', {}).get('name', 'Unknown Manufacturer')
                    logger.info(f"MPN{i+1}: {mpn}, Manufacturer{i+1}: {manufacturer_name}")
                    row = append_substitutes(row, i+1, manufacturer_name, mpn)
        except Exception as e:
            logger.error(f"Error resolving part with PK {part_pk}: {e}")
        updated_rows.append(row)
    return pd.DataFrame(updated_rows)

def main():
    parser = argparse.ArgumentParser(description="BOM parser CLI")
    parser.add_argument('-f', '--file', required=True, help='Path to the BOM file (CSV format)')
    load_dotenv()
    API_URL = os.getenv("INVENTREE_API_URL")
    API_USERNAME = os.getenv("INVENTREE_USERNAME")
    API_PASSWORD = os.getenv("INVENTREE_PASSWORD")
    api = InvenTreeAPI(API_URL, username=API_USERNAME, password=API_PASSWORD)
    args = parser.parse_args()
    df = process_bom_file(api, args.file)
    logger.info("\n" + df.head().to_string())
    output_file = os.path.splitext(args.file)[0] + '_resolved.csv'
    df.to_csv(output_file, index=False)
    logger.info(f"Resolved BOM saved to {output_file}")

if __name__ == "__main__":
    main()
