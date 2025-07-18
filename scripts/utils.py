import os
import pandas as pd
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part, Parameter, ParameterTemplate, PartCategoryParameterTemplate
import coloredlogs, logging
from tqdm import tqdm

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)

# Caches for entities
cache_part_category = {}
cache_company = {}
cache_part = {}
cache_parameter = {}
cache_parameter_template = {}
cache_part_category_parameter_template = {}

# Mapping of entity types to their caches
cache_mapping = {
    PartCategory: cache_part_category,
    Company: cache_company,
    Part: cache_part,
    Parameter: cache_parameter,
    ParameterTemplate: cache_parameter_template,
    PartCategoryParameterTemplate: cache_part_category_parameter_template
}

# Lookup Table for identifiers per entity type
identifier_lut = {
    Company: ['name'],
    Parameter: ['part', 'template'],
    ParameterTemplate: ['name'],
    Part: ['name', 'category'],
    PartCategory: ['name'],
    PartCategoryParameterTemplate: ['category', 'parameter_template']
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

    Returns:
    int or None
        The primary key of the created or existing entity, or None if an error occurs.
    """
    identifiers = identifier_lut.get(entity_type, [])
    if not identifiers:
        logger.error(f"No identifiers found for entity type: {entity_type.__name__}")
        return None
    
    cache = cache_mapping.get(entity_type, {})
    
    # Create a composite key from the identifiers
    composite_key = tuple(data[identifier] for identifier in identifiers if identifier in data)
    
    # Check cache first
    entity_id = cache.get(composite_key)
    if entity_id is not None:
        logger.debug(f"{entity_type.__name__} '{composite_key}' found in cache with ID: {entity_id}")
        return entity_id

    # Fetch all entities from the API and populate the cache
    entity_dict = {tuple(getattr(entity, identifier) for identifier in identifiers): entity.pk for entity in entity_type.list(api)}
    cache.update(entity_dict)

    # Check again after updating the cache
    entity_id = cache.get(composite_key)
    if entity_id is not None:
        logger.debug(f"{entity_type.__name__} '{composite_key}' already exists in database with ID: {entity_id}")
        return entity_id

    # Create new entity if not found
    try:
        new_entity = entity_type.create(api, data)
        logger.info(f"{entity_type.__name__} '{composite_key}' created successfully at ID: {new_entity.pk}")
        cache[composite_key] = new_entity.pk  # Update cache with new entity
        return new_entity.pk
    except Exception as e:
        logger.error(f"! Error creating {entity_type.__name__} '{composite_key}': {e}")
        return None

def process_csv_files(api, directory):
    """Process all CSV files in the specified directory."""
    # logger.setLevel(logging.CRITICAL)

    try:
        symbol_pk = resolve_entity(api, ParameterTemplate, {
            'name': 'symbol',
            'description': 'KiCad symbol path of the part',
            'default': 'Part.symbol'
        })
        footprint_pk = resolve_entity(api, ParameterTemplate, {
            'name': 'footprint',
            'description': 'KiCad footprint path of the part',
            'default': 'Part.footprint'
        })
    except Exception as e:
        logger.error(f"Error resolving ParameterTemplate: {e}")
        return



    for file in os.listdir(directory):
        if file.endswith('.csv'):
            logger.info(f"Processing '{file}'...")
            try:
                df = pd.read_csv(os.path.join(directory, file)).iloc[1:]  # Drop the 2nd row with the Units
                
                for _, row in df.iterrows():
                # for _, row in tqdm(df.iterrows(), total=df.shape[0], desc=f"Processing {file}"):
                    # skip very first two rows (header and units)

                    if row.isnull().all():
                        logger.warning(f"Skipping empty row: {row}")
                        continue

                    # ------------------------- category and subcategory ------------------------- #
                    if pd.isna(row['CATEGORY']) or pd.isna(row['NAME']):
                        logger.warning(f"Skipping row due to missing CATEGORY or NAME: {row}")
                        continue

                    category_pk = resolve_entity(api, PartCategory, {'name': row['CATEGORY']}) if row['CATEGORY'] else 0
                    
                    if pd.notna(row['SUBCATEGORY']) and row['SUBCATEGORY'].strip(): # only process non-empty subcategory
                        subcategory_pk = resolve_entity(api, PartCategory, {'name': row['SUBCATEGORY'], 'parent': category_pk})
                    else:
                        subcategory_pk = None

                    # PartCategoryParameterTemplate
                    try:
                        part_category_parameter_template_pk = resolve_entity(api, PartCategoryParameterTemplate, {
                            'category': subcategory_pk if subcategory_pk else category_pk,
                            'parameter_template': symbol_pk,
                            'default_value': '$'
                        })

                        logger.info(f"Created PartCategoryParameterTemplate ID: {part_category_parameter_template_pk}")
                    except Exception as e:
                        logger.error(f"Error creating PartCategoryParameterTemplate for Category '{category_pk}' and Subcategory '{subcategory_pk}': {e}")

                    # ----------------------------------- part ----------------------------------- #
                    part_data = {
                        'category': subcategory_pk if subcategory_pk else category_pk,
                        'name': row['NAME'],
                        'description': row['DESCRIPTION'] if not pd.isna(row['DESCRIPTION']) else '',
                        'copy_category_parameters': True,
                    }
                    

                    part_pk = resolve_entity(api, Part, part_data)


                    try:
                        resolve_entity(api, Parameter, {
                            'part': part_pk,
                            'template': symbol_pk,
                            'data': row['SYMBOL']})

                        # parameter_footprint_template_pk = resolve_entity(api, ParameterTemplate, {
                        #     'name': "footprint", 'default_value': 'my/default/path'})
                        # Parameter.create(api, {'part': part_pk, 'template': parameter_footprint_template_pk, 'data': row['FOOTPRINT']})
                    except Exception as e:
                        logger.error(f"Error creating Parameter for Part '{part_data['name']} ID {part_pk}': {e}")


                    # ------------------------ suppliers and manufacturers ----------------------- #
                    suppliers = [row[f'SUPPLIER{i}'] for i in range(1, 4)]
                    manufacturers = [row[f'MANUFACTURER{i}'] for i in range(1, 4)]
                    supplier_pks = [resolve_entity(api, Company, {'name': supplier, 'is_supplier': True, 'is_manufacturer': False}) for supplier in suppliers if pd.notna(supplier)]
                    manufacturer_pks = [resolve_entity(api, Company, {'name': manufacturer, 'is_supplier': False, 'is_manufacturer': True}) for manufacturer in manufacturers if pd.notna(manufacturer)]

                    for i, manufacturer_pk in enumerate(manufacturer_pks):
                        if manufacturer_pks[i] and pd.notna(row[f'MPN{i+1}']):
                            resolve_entity(api, ManufacturerPart, {'part': part_pk, 'manufacturer': manufacturer_pks[i], 'MPN': row[f'MPN{i+1}']})

                    for i, supplier_pk in enumerate(supplier_pks):
                        if supplier_pks[i] and pd.notna(row[f'SPN{i+1}']):
                            resolve_entity(api, SupplierPart, {'part': part_pk, 'supplier': supplier_pks[i], 'SKU': row[f'SPN{i+1}']})

            except Exception as e:
                logger.error(f"Error processing '{file}': {e}")