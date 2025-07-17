import os
import pandas as pd
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part, ParameterTemplate, Parameter
import coloredlogs, logging

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)

# Caches for entities
cache_part_category = {}
cache_company = {}
cache_part = {}
cache_parameter_template = {}

# Mapping of entity types to their caches
cache_mapping = {
    PartCategory: cache_part_category,
    Company: cache_company,
    Part: cache_part,
    ParameterTemplate: cache_parameter_template,
}

def resolve_entity(api, entity_type, data, identifier):
    """
    Find or create an entity in the InvenTree API based on a specified identifier.

    Parameters:
    api : object
        The API instance used to interact with the InvenTree server.
    entity_type : class
        The class type of the entity to be resolved or created (e.g., Part, Company).
    data : dict
        A dictionary containing the data required to create the entity if it does not exist.
    identifier : str
        The attribute name used to identify the entity (e.g., 'name', 'MPN').

    Returns:
    int or None
        The primary key of the created or existing entity, or None if an error occurs.
    """
    try:
        # Get the appropriate cache for the entity type
        cache = cache_mapping.get(entity_type, {})

        # Check cache first
        if data[identifier] in cache:
            logger.debug(f"{entity_type.__name__} '{data[identifier]}' found in cache!")
            return cache[data[identifier]]

        # Fetch all entities from the API and populate the cache
        entity_dict = {getattr(entity, identifier): entity.pk for entity in entity_type.list(api)}
        cache.update(entity_dict)

        if data[identifier] in cache:
            logger.debug(f"{entity_type.__name__} '{data[identifier]}' already exists in cache!")
            return cache[data[identifier]]
        else:
            logger.info(f"Creating new {entity_type.__name__} '{data[identifier]}'...")
            new_entity = entity_type.create(api, data)
            logger.info(f"{entity_type.__name__} '{data[identifier]}' created successfully!")
            cache[data[identifier]] = new_entity.pk  # Update cache with new entity
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
                print(df.head())
                for _, row in df.iterrows():
                    # skip very first two rows (header and units)
                    if row.isnull().all():
                        logger.warning(f"Skipping empty row: {row}")
                        continue

                    # ------------------------- category and subcategory ------------------------- #
                    if pd.isna(row['CATEGORY']) or pd.isna(row['NAME']):
                        logger.warning(f"Skipping row due to missing CATEGORY or NAME: {row}")
                        continue

                    category_pk = resolve_entity(api, PartCategory, {'name': row['CATEGORY']}, 'name') if row['CATEGORY'] else 0
                    
                    if pd.notna(row['SUBCATEGORY']) and row['SUBCATEGORY'].strip(): # only process non-empty subcategory
                        subcategory_pk = resolve_entity(api, PartCategory, {'name': row['SUBCATEGORY'], 'parent': category_pk}, 'name')
                    else:
                        subcategory_pk = None

                    # ----------------------------------- part ----------------------------------- #
                    part_data = {
                        'category': subcategory_pk if subcategory_pk else category_pk,
                        'name': row['NAME'],
                        'description': row['DESCRIPTION'] if not pd.isna(row['DESCRIPTION']) else ''
                    }
                    part_pk = resolve_entity(api, Part, part_data, 'name')

                    # ------------------------ suppliers and manufacturers ----------------------- #
                    suppliers = [row[f'SUPPLIER{i}'] for i in range(1, 4)]
                    manufacturers = [row[f'MANUFACTURER{i}'] for i in range(1, 4)]
                    supplier_pks = [resolve_entity(api, Company, {'name': supplier, 'is_supplier': True, 'is_manufacturer': False}, 'name') for supplier in suppliers if pd.notna(supplier)]
                    manufacturer_pks = [resolve_entity(api, Company, {'name': manufacturer, 'is_supplier': False, 'is_manufacturer': True}, 'name') for manufacturer in manufacturers if pd.notna(manufacturer)]

                    for i, manufacturer_pk in enumerate(manufacturer_pks):
                        if manufacturer_pks[i] and pd.notna(row[f'MPN{i+1}']):
                            resolve_entity(api, ManufacturerPart, {'part': part_pk, 'manufacturer': manufacturer_pks[i], 'MPN': row[f'MPN{i+1}']}, 'MPN')

                    for i, supplier_pk in enumerate(supplier_pks):
                        if supplier_pks[i] and pd.notna(row[f'SPN{i+1}']):
                            resolve_entity(api, SupplierPart, {'part': part_pk, 'supplier': supplier_pks[i], 'SKU': row[f'SPN{i+1}']}, 'SKU')

            except Exception as e:
                logger.error(f"Error processing '{file}': {e}")

def create_parameter_templates(api):
    resolve_entity(api, ParameterTemplate, {
        'name': 'symbol',
        'description': 'KiCad symbol path of the part'
    }, 'name')
    resolve_entity(api, ParameterTemplate, {
        'name': 'footprint',
        'description': 'KiCad footprint path of the part'
    }, 'name')