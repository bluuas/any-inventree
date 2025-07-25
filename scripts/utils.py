import os
import pandas as pd
from inventree.api import InvenTreeAPI
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part, Parameter, ParameterTemplate, PartCategoryParameterTemplate
from inventree.plugin import InvenTreePlugin
import coloredlogs, logging
from tqdm import tqdm
import requests

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)

# SITE_URL = os.getenv("INVENTREE_SITE_URL")
INVENTREE_SITE_URL="http://inventree.localhost" # todo: replace with the .env variable from the parent directory

# Caches for entities to speed up lookups
cache_company = {}
cache_parameter = {}
cache_parameter_template = {}
cache_part = {}
cache_part_category = {}
cache_part_category_parameter_template = {}

# counter for the (dummy) Internal Part Number IPN
ipn_counter = 100000

# Mapping of entity types to their caches
cache_mapping = {
    Company: cache_company,
    Parameter: cache_parameter,
    ParameterTemplate: cache_parameter_template,
    Part: cache_part,
    PartCategory: cache_part_category,
    PartCategoryParameterTemplate: cache_part_category_parameter_template,
}

# Lookup Table for identifiers per entity type
identifier_lut = {
    Company: ['name'],
    ManufacturerPart: ['MPN'],
    Parameter: ['part', 'template'],
    ParameterTemplate: ['name'],
    Part: ['name', 'category'],
    PartCategory: ['name'],
    PartCategoryParameterTemplate: ['category', 'parameter_template'],
    SupplierPart: ['SKU'],
}

# lookup table for schematic reference designators
def resolve_reference_designator(part_category_name):
    reference_lut = {
        'Capacitors': 'C',
        'Connectors': 'J',
        'Integrated Circuits': 'U',
        'LED': 'D',
        'Resistors': 'R',
    }
    if part_category_name in reference_lut:
        return reference_lut[part_category_name]
    else:
        logger.error(f"No reference designator found for part category: {part_category_name}")
        return ''

def resolve_entity(api, entity_type, data):
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
def delete_all(api: InvenTreeAPI):
    """
    Delete all parts, other entities, and related data from the InvenTree database.
    Does not reset the \'pk' values from the database.

    Parameters:
    api : object
    """
    # Step 1: Delete all parts
    parts_dict = Part.list(api)
    logger.info(f"Deleting {len(parts_dict)} parts")
    
    for part in parts_dict:
        try:
            logger.debug(f"Deactivating part: {part.name} with PK: {part.pk}")
            part.save(data={
                'active': False,
                'name': f"{part.name}",
                'minimum_stock': 0,
            }, method='PUT')  # Use PUT to update the part
            logger.debug(f"Deleting part: {part.name} with PK: {part.pk}")
            part.delete()  # Now delete the part
        except Exception as e:
            logger.error(f"Error processing part '{part.name}': {e}")

    # Step 2: Delete other entities
    for entity_type, cache in cache_mapping.items():
        try:
            entities = entity_type.list(api)
            logger.debug(f"Deleting {len(entities)} instances of {entity_type.__name__}")
            for entity in entities:
                entity.delete()
            cache.clear()
        except Exception as e:
            logger.error(f"Error deleting {entity_type.__name__} instances: {e}")

def process_csv_file(api: InvenTreeAPI, file):
    logger.setLevel(logging.INFO)

    HEADERS = {
        "Authorization": f"Token {api.token}",
        "Content-Type": "application/json"
    }

    try:
        df = pd.read_csv(file).iloc[1:]  # Drop the 2nd row with the Units
        logger.info(f"Processing {df.shape[0]} row(s) from {file}")
        for _, row in df.iterrows():
        # for _, row in tqdm(df.iterrows(), total=df.shape[0], desc=f"Processing {file}"):

            if row.isnull().all():
                logger.warning(f"Skipping empty row: {row}")
                continue

            # ------------------------- category and subcategory ------------------------- #
            if pd.isna(row['CATEGORY']) or pd.isna(row['NAME']):
                logger.warning(f"Skipping row due to missing CATEGORY or NAME: {row}")
                continue

            part_category_pk = resolve_entity(api, PartCategory, {'name': row['CATEGORY']}) if row['CATEGORY'] else 0
            # add the category also to the KiCad plugin
            requests.post(f"{INVENTREE_SITE_URL}/plugin/kicad-library-plugin/api/category/", headers=HEADERS, json={'category': part_category_pk})

            if pd.notna(row['SUBCATEGORY']) and row['SUBCATEGORY'].strip(): # only process non-empty subcategory
                part_subcategory_pk = resolve_entity(api, PartCategory, {'name': row['SUBCATEGORY'], 'parent': part_category_pk})
                requests.post(f"{INVENTREE_SITE_URL}/plugin/kicad-library-plugin/api/category/", headers=HEADERS, json={
                    'category': part_subcategory_pk,
                    'default_reference': resolve_reference_designator(row['SUBCATEGORY'])
                })
            else:
                part_subcategory_pk = None

            # --------------------------- name and description --------------------------- #
            part_name = row['NAME'] if not pd.isna(row['NAME']) else ''
            part_description = row['DESCRIPTION'] if not pd.isna(row['DESCRIPTION']) else ''

            # ----------------------------------- part ----------------------------------- #
            try:
                global ipn_counter
                part_data = {
                    'category': part_subcategory_pk if part_subcategory_pk else part_category_pk,
                    'name': part_name,
                    'description': part_description,
                    'IPN': ipn_counter
                }
                part_pk = resolve_entity(api, Part, part_data)
                ipn_counter += 1
            except Exception as e:
                logger.error(f"Error creating Part: {e}")
            # -------------------------------- parameters -------------------------------- #
            # get all the parameters inbetween the DESCRIPTION and MANUFACTURER1 columns from left to right
            try:
                parameters = [row.iloc[i] for i in range(df.columns.get_loc('DESCRIPTION'), df.columns.get_loc('MANUFACTURER1')) if not pd.isna(row.iloc[i])]
                # create parameter templates
                for i, parameter in enumerate(parameters):
        
                    parameter_template_pk = resolve_entity(api, ParameterTemplate, {
                        'name': df.columns[i+df.columns.get_loc('DESCRIPTION')],
                        })
                    parameter_pk = resolve_entity(api, Parameter, {
                        'part': part_pk,
                        'template': parameter_template_pk,
                        'data': parameter
                        })
                logger.debug(f"Parameters: {parameters}")
            except Exception as e:
                logger.error(f"Error creating Parameters: {e}")

            # ------------------------ suppliers and manufacturers ----------------------- #
            suppliers = [row[f'SUPPLIER{i}'] for i in range(1, 4)]
            manufacturers = [row[f'MANUFACTURER{i}'] for i in range(1, 4)]

            # Initialize lists to hold primary keys
            manufacturer_part_pks = []

            # Single loop to resolve entities and create parts
            for i in range(3):
                supplier = suppliers[i]
                manufacturer = manufacturers[i]
                
                if pd.notna(supplier):
                    supplier_pk = resolve_entity(api, Company, {'name': supplier, 'is_supplier': True, 'is_manufacturer': False})
                
                if pd.notna(manufacturer):
                    manufacturer_pk = resolve_entity(api, Company, {'name': manufacturer, 'is_supplier': False, 'is_manufacturer': True})
                    
                    if manufacturer_pk and pd.notna(row[f'MPN{i+1}']):
                        manufacturer_part_pk = resolve_entity(api, ManufacturerPart, {'part': part_pk, 'manufacturer': manufacturer_pk, 'MPN': row[f'MPN{i+1}']})
                        manufacturer_part_pks.append(manufacturer_part_pk)
                
                if supplier_pk and pd.notna(row[f'SPN{i+1}']):
                    resolve_entity(api, SupplierPart, {
                        'part': part_pk,
                        'supplier': supplier_pk,
                        'SKU': row[f'SPN{i+1}'],
                        'manufacturer_part': manufacturer_part_pks[i] if i < len(manufacturer_part_pks) else None
                    })
                    
    except Exception as e:
        logger.error(f"Error processing '{file}': {e}")

def install_kicad_plugin(api: InvenTreeAPI):
    try:
        plugins = InvenTreePlugin.list(api)

        # Check if the KiCad plugin is already installed
        kicad_plugin = next((plugin for plugin in plugins if plugin.pk == "kicad-library-plugin"), None)
        
        if kicad_plugin:
            return  # Finish if the KiCad plugin is already installed

        # Install the KiCad plugin
        response = api.request(api_url="plugins/install", method="POST", data={
            'packagename': 'inventree-kicad-plugin',
            'confirm': True,
        }) 

        logger.info(f"Installed InvenTree plugin: {response.json()}")

        # Activate the newly installed KiCad plugin
        kicad_plugin = next((plugin for plugin in plugins if plugin.pk == "kicad-library-plugin"), None)
        if kicad_plugin:
            kicad_plugin.setActive(True)
            logger.info(f"Activated InvenTree plugin: {kicad_plugin.pk}")

    except Exception as e:
        logger.error(f"Error installing KiCad plugin: {e}")

def update_kicad_plugin(api: InvenTreeAPI):
    # update the KiCad plugin settings with the pk's for Footprint, Symbol, Reference and Value Parameter
    
    # Get the primary keys for Footprint, Symbol, Reference and Value Parameter
    footprint_pk = resolve_entity(api, ParameterTemplate, {'name': 'FOOTPRINT'})
    symbol_pk = resolve_entity(api, ParameterTemplate, {'name': 'SYMBOL'})
    # reference_pk = resolve_entity(api, ParameterTemplate, {'name': 'Reference'})
    value_pk = resolve_entity(api, ParameterTemplate, {'name': 'VALUE'})

    # Update the settings
    settings_url = f"{INVENTREE_SITE_URL}/plugins/kicad-library-plugin/settings/"
    settings = {
        'KICAD_FOOTPRINT_PARAMETER': footprint_pk,
        'KICAD_SYMBOL_PARAMETER': symbol_pk,
        # 'KICAD_REFERENCE_PARAMETER': reference_pk,
        'KICAD_VALUE_PARAMETER': value_pk,
    }

    try:
        for key, value in settings.items():
            response = api.request(api_url=f"{settings_url}{key}/", method="PATCH", data={'value': value})
            logger.info(f"response: {response.json()}")
    except Exception as e:
        logger.error(f"Error updating KiCad plugin settings: {e}")