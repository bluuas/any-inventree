import os
import pandas as pd
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part
import coloredlogs, logging

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)

def resolve_entity(api, entity_type, data, identifier):
    """Find or create an entity in the InvenTree API based on a specified identifier."""
    try:
        entity_dict = {getattr(entity, identifier): entity.pk for entity in entity_type.list(api)}
        if data[identifier] in entity_dict:
            logger.debug(f"{entity_type.__name__} '{data[identifier]}' already exists!")
            return entity_dict[data[identifier]]
        else:
            logger.info(f"Creating new {entity_type.__name__} '{data[identifier]}'...")
            new_entity = entity_type.create(api, data)
            logger.info(f"{entity_type.__name__} '{data[identifier]}' created successfully!")
            return new_entity.pk
    except Exception as e:
        logger.error(f"Error creating {entity_type.__name__} '{data[identifier]}': {e}")
        return None

def process_csv_files(api, directory):
    """Process all CSV files in the specified directory."""
    for file in os.listdir(directory):
        if file.endswith('.csv'):
            logger.info(f"Processing '{file}'...")
            try:
                df = pd.read_csv(os.path.join(directory, file)).iloc[1:]  # Drop the 2nd row with the Units

                for _, row in df.iterrows():
                    # skip very first two rows (header and units)
                    if row.isnull().all():
                        logger.warning(f"Skipping empty row: {row}")
                        continue

                    # Check for NaN or empty cells
                    if pd.isna(row['CATEGORY']) or pd.isna(row['NAME']):
                        logger.warning(f"Skipping row due to missing CATEGORY or NAME: {row}")
                        continue

                    category_pk = resolve_entity(api, PartCategory, {'name': row['CATEGORY']}, 'name') if row['CATEGORY'] else 0
                    
                    if pd.notna(row['SUBCATEGORY']) and row['SUBCATEGORY'].strip(): # only process non-empty subcategory
                        subcategory_pk = resolve_entity(api, PartCategory, {'name': row['SUBCATEGORY'], 'parent': category_pk}, 'name')
                    else:
                        subcategory_pk = None
                    part_data = {
                        'category': subcategory_pk if subcategory_pk else category_pk,
                        'name': row['NAME'],
                        'description': row['DESCRIPTION'] if not pd.isna(row['DESCRIPTION']) else ''
                    }
                    part_pk = resolve_entity(api, Part, part_data, 'name')

                    suppliers = [row[f'SUPPLIER{i}'] for i in range(1, 4)]
                    manufacturers = [row[f'MANUFACTURER{i}'] for i in range(1, 4)]
                    supplier_pks = [resolve_entity(api, Company, {'name': supplier, 'is_supplier': True, 'is_manufacturer': False}, 'name') for supplier in suppliers if pd.notna(supplier)]
                    manufacturer_pks = [resolve_entity(api, Company, {'name': manufacturer, 'is_supplier': False, 'is_manufacturer': True}, 'name') for manufacturer in manufacturers if pd.notna(manufacturer)]

                    for i in range(min(3, len(manufacturer_pks))):  # Only iterate over available manufacturers
                        if manufacturer_pks[i] and pd.notna(row[f'MPN{i+1}']):
                            resolve_entity(api, ManufacturerPart, {'part': part_pk, 'manufacturer': manufacturer_pks[i], 'MPN': row[f'MPN{i+1}']}, 'MPN')

                    for i in range(min(3, len(supplier_pks))):  # Only iterate over available suppliers
                        if supplier_pks[i] and pd.notna(row[f'SPN{i+1}']):
                            resolve_entity(api, SupplierPart, {'part': part_pk, 'supplier': supplier_pks[i], 'SKU': row[f'SPN{i+1}']}, 'SKU')

            except Exception as e:
                logger.error(f"Error processing '{file}': {e}")
