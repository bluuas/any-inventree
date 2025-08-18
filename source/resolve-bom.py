from inventree.api import InvenTreeAPI
from inventree.part import PartRelated
import os
import argparse
import logging
import pprint
import pandas as pd
import coloredlogs
from utils.error_codes import ErrorCodes
from utils.config import Config

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)

def append_substitutes(row, i, manufacturer_name, mpn):
    """
    Update a row with MPN and manufacturer name for the i-th substitute.
    Returns error code.
    """
    try:
        if not manufacturer_name or not mpn:
            logger.warning(f"Empty manufacturer name or MPN for substitute {i}")
            return ErrorCodes.INVALID_DATA
        
        row[f"Manufacturer{i}"] = manufacturer_name
        row[f"MPN{i}"] = mpn
        return ErrorCodes.SUCCESS
    except Exception as e:
        logger.error(f"Error updating substitute {i}: {e}")
        return ErrorCodes.API_ERROR

def process_bom_file(api, file_path):
    """
    Process BOM file and resolve part relations.
    Returns (DataFrame, error_code).
    """
    try:
        df = pd.read_csv(file_path)
        logger.debug("\n" + df.head().to_string())
    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {e}")
        return None, ErrorCodes.FILE_ERROR

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
            
            if not relations:
                logger.info(f"No relations found for part PK {part_pk}")
                updated_rows.append(row)
                continue
                
            logger.debug(f"Found {len(relations)} relations for part PK {part_pk}: {relations}")
            
            for i, rel in enumerate(relations[:3]):  # Only up to 3 substitutes
                try:
                    rel_response = api.get(f"part/related/{rel.pk}/")
                    part_related_pk = rel_response.get('part_2')
                    
                    if not part_related_pk:
                        logger.warning(f"No part_2 found in relation {rel.pk}")
                        continue
                        
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
                        
                        error_code = append_substitutes(row, i+1, manufacturer_name, mpn)
                        if error_code != ErrorCodes.SUCCESS:
                            logger.warning(f"Failed to append substitute {i+1} for part {part_pk}")
                    else:
                        logger.warning(f"No manufacturer parts found for part {part_related_pk}")
                        
                except Exception as e:
                    logger.error(f"Error processing relation {rel.pk}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error resolving part with PK {part_pk}: {e}")
            
        updated_rows.append(row)
        
    return pd.DataFrame(updated_rows), ErrorCodes.SUCCESS

def main():
    parser = argparse.ArgumentParser(description="BOM parser CLI")
    parser.add_argument('-f', '--file', required=True, help='Path to the BOM file (CSV format)')
    
    try:
        # Validate required configuration
        missing_vars = Config.validate_required()
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            return ErrorCodes.CONFIGURATION_ERROR
            
        credentials = Config.get_api_credentials()
        api = InvenTreeAPI(credentials['url'], username=credentials['username'], password=credentials['password'])
        args = parser.parse_args()
        
        df, error_code = process_bom_file(api, args.file)
        if error_code != ErrorCodes.SUCCESS:
            logger.error(f"Failed to process BOM file with error code: {error_code}")
            return error_code
            
        logger.info("\n" + df.head().to_string())
        output_file = os.path.splitext(args.file)[0] + '_resolved.csv'
        df.to_csv(output_file, index=False)
        logger.info(f"Resolved BOM saved to {output_file}")
        return ErrorCodes.SUCCESS
        
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        return ErrorCodes.API_ERROR

if __name__ == "__main__":
    main()
