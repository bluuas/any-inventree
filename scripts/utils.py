import os
import pandas as pd
from inventree.api import InvenTreeAPI
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part, Parameter, ParameterTemplate, PartRelated
from inventree.plugin import InvenTreePlugin
import coloredlogs, logging
from tqdm import tqdm
import requests

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)

INVENTREE_SITE_URL="http://inventree.localhost" # todo: replace with the .env variable from the parent directory
KICAD_PLUGIN_PK = "kicad-library-plugin" # todo: naming consistency

# Caches for entities to speed up lookups
cache_company = {}
cache_parameter = {}
cache_parameter_template = {}
cache_part = {}
cache_part_category = {}
cache_part_category_parameter_template = {}
cache_part_related = {}

# counter for the (dummy) Internal Part Number IPN
ipn_counter = 100000

# Mapping of entity types to their caches
CACHE_MAPPING = {
    Company: cache_company,
    Parameter: cache_parameter,
    ParameterTemplate: cache_parameter_template,
    Part: cache_part,
    PartCategory: cache_part_category,
    PartRelated: cache_part_related,
}

# Lookup Table for identifiers per entity type
IDENTIFIER_LUT = {
    Company: ['name'],
    ManufacturerPart: ['MPN'],
    Parameter: ['part', 'template'],
    ParameterTemplate: ['name'],
    Part: ['name', 'category'],
    PartCategory: ['name', 'parent'],
    PartRelated: ['part_1', 'part_2'],
    SupplierPart: ['SKU'],
}

# lookup table for schematic reference designators
def resolve_reference_designator(part_category_name):
    reference_lut = {
        'Capacitors': 'C',
        'Connectors': 'J',
        'JST': 'J',
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
    identifiers = IDENTIFIER_LUT.get(entity_type, [])
    if not identifiers:
        logger.error(f"No identifiers found for entity type: {entity_type.__name__}")
        return None
    
    cache = CACHE_MAPPING.get(entity_type, {})
    
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
    for entity_type, cache in CACHE_MAPPING.items():
        try:
            entities = entity_type.list(api)
            logger.debug(f"Deleting {len(entities)} instances of {entity_type.__name__}")
            for entity in entities:
                entity.delete()
            cache.clear()
        except Exception as e:
            logger.error(f"Error deleting {entity_type.__name__} instances: {e}")
 
def process_row(api: InvenTreeAPI, row: pd.Series):

    # Resolve categories and subcategories
    part_category_pk = resolve_entity(api, PartCategory, {'name': row['CATEGORY'], 'parent': None, 'structural': True})
    part_subcategory_pk = resolve_entity(api, PartCategory, {'name': row['SUBCATEGORY'], 'parent': part_category_pk})
    part_subcategory_generic_pk = resolve_entity(api, PartCategory, {'name': 'generic', 'parent': part_subcategory_pk})
    part_subcategory_critical_pk = resolve_entity(api, PartCategory, {'name': 'critical', 'parent': part_subcategory_pk})
    part_subcategory_manufactured_pk = resolve_entity(api, PartCategory, {'name':'manufactured', 'parent': part_subcategory_pk})
       
    HEADERS = {
        "Authorization": f"Token {api.token}",
        "Content-Type": "application/json"
    }

    # requests.post(f"{INVENTREE_SITE_URL}/plugin/{KICAD_PLUGIN_PK}/api/category/", headers=HEADERS, json={
    #     'category': part_subcategory_generic_pk,
    #     'default_reference': resolve_reference_designator(row['SUBCATEGORY'])
    # })

    # --------------------------- Name and description --------------------------- #
    part_name_generic = f"{row['NAME']}_generic"
    # part_name_critical = f"{row['NAME']}_critical"
    part_name_manufacturer1 = f"{row['NAME']}_{row[f'MANUFACTURER1']}_{row[f'MPN1']}".replace(" ", "_")
    part_name_manufacturer2 = f"{row['NAME']}_{row[f'MANUFACTURER2']}_{row[f'MPN2']}".replace(" ", "_")
    part_name_manufacturer3 = f"{row['NAME']}_{row[f'MANUFACTURER3']}_{row[f'MPN3']}".replace(" ", "_")
    part_description = row['DESCRIPTION'] if not pd.isna(row['DESCRIPTION']) else ''

    # -------------------- Create parts for each category type ------------------- #
    part_generic_pk = resolve_entity(api, Part, {
            'name': part_name_generic,
            'category': part_subcategory_generic_pk,
            'description': part_description,
            'virtual': True,
        })
    # todo: update part with its own link in the datasheet field
    
    # part_critical_pk = resolve_entity(api, Part, {
    #         'name': part_name_critical,
    #         'category': part_subcategory_critical_pk,
    #         'description': part_description,
    #         'virtual': True,
    #     })
    part_manufacturer1_pk = resolve_entity(api, Part, {
            'name': part_name_manufacturer1,
            'category': part_subcategory_manufactured_pk,
            'description': part_description,
        })
    resolve_entity(api, PartRelated, {
        'part_1': part_generic_pk,
        'part_2': part_manufacturer1_pk,
    })
    part_manufacturer2_pk = resolve_entity(api, Part, {
        'name': part_name_manufacturer2,
            'category': part_subcategory_manufactured_pk,
            'description': part_description,
        })
    resolve_entity(api, PartRelated, {
        'part_1': part_generic_pk,
        'part_2': part_manufacturer2_pk,
    })
    part_manufacturer3_pk = resolve_entity(api, Part, {
        'name': part_name_manufacturer3,
            'category': part_subcategory_manufactured_pk,
            'description': part_description,
        })
    resolve_entity(api, PartRelated, {
        'part_1': part_generic_pk,
        'part_2': part_manufacturer3_pk,
    })

    # -------------------------------- Parameters -------------------------------- #
    try:
        description_index = row.index.get_loc('DESCRIPTION')
        manufacturer1_index = row.index.get_loc('MANUFACTURER1')
        
        parameters = [row.iloc[i] for i in range(description_index + 1, manufacturer1_index) if not pd.isna(row.iloc[i])]
        logger.debug(f"Parameters: {parameters}")

        for i, parameter in enumerate(parameters):
            parameter_template_pk = resolve_entity(api, ParameterTemplate, {
                'name': row.index[description_index + 1 + i],
            })

            resolve_entity(api, Parameter, {
                'part': part_generic_pk,
                'template': parameter_template_pk,
                'data': parameter
            })
            # resolve_entity(api, Parameter, {
            #     'part': part_critical_pk,
            #     'template': parameter_template_pk,
            #     'data': parameter
            # })
            resolve_entity(api, Parameter, {
                'part': part_manufacturer1_pk,
                'template': parameter_template_pk,
                'data': parameter
            })
            resolve_entity(api, Parameter, {
                'part': part_manufacturer2_pk,
                'template': parameter_template_pk,
                'data': parameter
            })
            resolve_entity(api, Parameter, {
                'part': part_manufacturer3_pk,
                'template': parameter_template_pk,
                'data': parameter
            })

    except Exception as e:
        logger.error(f"Error creating Parameters: {e}")


    # ------------------------ Suppliers and manufacturers ----------------------- #
    manufacturers = [row[f'MANUFACTURER{i}'] for i in range(1, 4)]
    suppliers = [row[f'SUPPLIER{i}'] for i in range(1, 4)]
    part_manufacturer_pks = [part_manufacturer1_pk, part_manufacturer2_pk, part_manufacturer3_pk]
    
    for i in range(1):
        manufacturer = manufacturers[i]
        supplier = suppliers[i]

        if pd.notna(manufacturer):
            manufacturer_pk = resolve_entity(api, Company, {'name': manufacturer, 'is_supplier': False, 'is_manufacturer': True})
            
            if manufacturer_pk and pd.notna(row[f'MPN{i+1}']):
                manufacturer_part_pk = resolve_entity(api, ManufacturerPart, {
                    'part': part_manufacturer_pks[i],
                    'manufacturer': manufacturer_pk,
                    'MPN': row[f'MPN{i+1}']
                })

        if pd.notna(supplier):
            supplier_pk = resolve_entity(api, Company, {'name': supplier, 'is_supplier': True, 'is_manufacturer': False})
            if supplier_pk and pd.notna(row[f'SPN{i+1}']):
                supplier_part_pk = resolve_entity(api, SupplierPart, {
                    'part': part_manufacturer_pks[i],
                    'supplier': supplier_pk,
                    'SKU': row[f'SPN{i+1}'],
                    'manufacturer_part': manufacturer_part_pk
                })

    logger.info(f"Processed row successfully: {row['NAME']}")

def process_csv_file(api: InvenTreeAPI, filename: str):
    # logger.setLevel(logging.INFO)
    try:
        df = pd.read_csv(filename).iloc[1:]  # Drop the 2nd row with the Units
        logger.info(f"Processing {df.shape[0]} row(s) from {filename}")
        for _, row in df.iterrows():
            process_row(api, row)                    
    except Exception as e:
        logger.error(f"Error processing '{filename}': {e}")

# Constants for settings and plugin keys
INVENTREE_GLOBAL_SETTINGS = {
    "ENABLE_PLUGINS_URL",
    "ENABLE_PLUGINS_APP"
}

def configure_inventree_plugin_settings(api: InvenTreeAPI):
    try:
        for setting in INVENTREE_GLOBAL_SETTINGS:
            response_data = api.patch(url=f"settings/global/{setting}/", data={'value': True})
            if response_data is None:
                logger.error(f"Failed to set global setting {setting}.")
                return
            logger.info(f"Set global setting {setting} to True.")
    except Exception as e:
        logger.error(f"Error configuring global settings: {e}")

def install_and_activate_kicad_plugin(api: InvenTreeAPI):
    try:
        plugins = InvenTreePlugin.list(api)
        for plugin in plugins:
            logger.debug(f"Plugin: pk: {plugin.pk}, name: {plugin.name}")

        kicad_plugin = next((plugin for plugin in plugins if plugin.pk == KICAD_PLUGIN_PK), None)
        
        if kicad_plugin:
            logger.info("KiCad plugin is already installed. Trying to activate.")
        else:
            response_data = api.post(url="plugins/install", data={
                'url': 'git+https://github.com/bluuas/inventree_kicad',
                'packagename': KICAD_PLUGIN_PK,
                'confirm': True,
            })
            if response_data is None:
                logger.error("Failed to install InvenTree plugin.")
                return
            logger.info(f"Installed InvenTree plugin: {response_data}")

        response_data = api.patch(url=f"plugins/{KICAD_PLUGIN_PK}/activate/", data={'active': True})
        if response_data is None:
            logger.error("Failed to activate KiCad plugin.")
            return
        logger.info("KiCad plugin is active.")
    except Exception as e:
        logger.error(f"Error installing or activating KiCad plugin: {e}")

def update_kicad_plugin(api: InvenTreeAPI):
    try:
        # Resolve primary keys for parameters
        footprint_pk = resolve_entity(api, ParameterTemplate, {'name': 'FOOTPRINT'})
        symbol_pk = resolve_entity(api, ParameterTemplate, {'name': 'SYMBOL'})
        designator_pk = resolve_entity(api, ParameterTemplate, {'name': 'DESIGNATOR'})
        value_pk = resolve_entity(api, ParameterTemplate, {'name': 'VALUE'})

        settings = {
            'KICAD_FOOTPRINT_PARAMETER': footprint_pk,
            'KICAD_SYMBOL_PARAMETER': symbol_pk,
            'KICAD_REFERENCE_PARAMETER': designator_pk,
            'KICAD_VALUE_PARAMETER': value_pk,
        }

        for key, value in settings.items():
            response_data = api.patch(url=f"plugins/{KICAD_PLUGIN_PK}/settings/{key}/", data={'value': value})
            if response_data is None:
                logger.error(f"Failed to update setting {key}.")
                return
            logger.info(f"Updated KiCad setting {key} to {value}.")
    except Exception as e:
        logger.error(f"Error updating KiCad plugin settings: {e}")