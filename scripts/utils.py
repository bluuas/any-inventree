import os
import pandas as pd
from inventree.api import InvenTreeAPI
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part, Parameter, ParameterTemplate, PartRelated
import coloredlogs
import logging

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)

INVENTREE_SITE_URL = os.getenv("INVENTREE_SITE_URL", "http://inventree.localhost")
KICAD_PLUGIN_PK = "kicad-library-plugin"

# Caches for entities to speed up lookups
caches = {
    Company: {},
    ManufacturerPart: {},
    Parameter: {},
    ParameterTemplate: {},
    Part: {},
    PartCategory: {},
    PartRelated: {},
    SupplierPart: {},
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

# Lookup table for schematic reference designators
REFERENCE_LUT = {
    'Capacitors': 'C',
    'Connectors': 'J',
    'JST': 'J',
    'Integrated Circuits': 'U',
    'LED': 'D',
    'Resistors': 'R',
}

def resolve_reference_designator(part_category_name):
    return REFERENCE_LUT.get(part_category_name, '')

def resolve_entity(api, entity_type, data):
    identifiers = IDENTIFIER_LUT.get(entity_type, [])
    if not identifiers:
        logger.error(f"No identifiers found for entity type: {entity_type.__name__}")
        return None
    
    try:
        cache = caches[entity_type]
        composite_key = tuple(data[identifier] for identifier in identifiers if identifier in data)
    except Exception as e:
        logger.error(f"Error resolving entity in cache: {e}")
        return None

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
        cache[composite_key] = new_entity.pk
        return new_entity.pk
    except Exception as e:
        logger.error(f"! Error creating {entity_type.__name__} '{composite_key}': {e}")
        return None

def delete_all(api: InvenTreeAPI):
    parts = Part.list(api)
    logger.info(f"Deleting {len(parts)} parts")
    
    for part in parts:
        try:
            logger.debug(f"Deactivating part: {part.name} with PK: {part.pk}")
            part.save(data={
                'active': False,
                'name': f"{part.name}",
                'minimum_stock': 0,
            }, method='PUT')
            logger.debug(f"Deleting part: {part.name} with PK: {part.pk}")
            part.delete()
        except Exception as e:
            logger.error(f"Error processing part '{part.name}': {e}")

    for entity_type, cache in caches.items():
        try:
            entities = entity_type.list(api)
            logger.debug(f"Deleting {len(entities)} instances of {entity_type.__name__}")
            for entity in entities:
                entity.delete()
            cache.clear()
        except Exception as e:
            logger.error(f"Error deleting {entity_type.__name__} instances: {e}")

def process_row(api: InvenTreeAPI, row: pd.Series):
    part_category_pk = resolve_entity(api, PartCategory, {'name': row['CATEGORY'], 'parent': None, 'structural': True})
    part_subcategory_pk = resolve_entity(api, PartCategory, {'name': row['SUBCATEGORY'], 'parent': part_category_pk})

    HEADERS = {
        "Authorization": f"Token {api.token}",
        "Content-Type": "application/json"
    }

    part_name_generic = f"{row['NAME']}_generic"
    part_description = row['DESCRIPTION'] if not pd.isna(row['DESCRIPTION']) else ''

    try:
        # Create parts for each category type
        part_generic_pk = resolve_entity(api, Part, {
            'name': part_name_generic,
            'category': part_subcategory_pk,
            'description': part_description,
            'virtual': True,
        })
    except Exception as e:
        logger.error(f"Error creating generic part '{part_name_generic}': {e}")
        return
    
    try:
        part_manufacturer_pks = []
        for i in range(1, 4):
            manufacturer_name = row[f'MANUFACTURER{i}']
            if pd.notna(manufacturer_name):
                part_name_manufacturer = f"{row['NAME']}_{manufacturer_name}_{row[f'MPN{i}']}".replace(" ", "_")
                part_manufacturer_pk = resolve_entity(api, Part, {
                    'name': part_name_manufacturer,
                    'category': part_subcategory_pk,
                    'description': part_description,
                })
                part_manufacturer_pks.append(part_manufacturer_pk)

                # Create relationships between generic and manufacturer parts
                resolve_entity(api, PartRelated, {
                    'part_1': part_generic_pk,
                    'part_2': part_manufacturer_pk,
                })
    except Exception as e:
        logger.error(f"Error creating Manufacturer Parts: {e}")

    # Handle parameters
    try:
        description_index = row.index.get_loc('DESCRIPTION')
        manufacturer1_index = row.index.get_loc('MANUFACTURER1')
        
        parameters = [row.iloc[i] for i in range(description_index + 1, manufacturer1_index) if not pd.isna(row.iloc[i])]
        logger.debug(f"Parameters: {parameters}")

        for i, parameter in enumerate(parameters):
            parameter_template_pk = resolve_entity(api, ParameterTemplate, {
                'name': row.index[description_index + 1 + i],
            })

            for part_pk in [part_generic_pk] + part_manufacturer_pks:
                resolve_entity(api, Parameter, {
                    'part': part_pk,
                    'template': parameter_template_pk,
                    'data': parameter
                })

    except Exception as e:
        logger.error(f"Error creating Parameters: {e}")

    # Handle suppliers and manufacturers
    try:
        for i in range(1, 4):
            manufacturer_name = row[f'MANUFACTURER{i}']
            supplier_name = row[f'SUPPLIER{i}']

            # skip if manufacturer or supplier is empty
            if pd.isna(manufacturer_name):  # Check for non-empty manufacturer
                logger.debug(f"Skipping manufacturer or supplier because it is empty")
                continue

            manufacturer_pk = resolve_entity(api, Company, {'name': manufacturer_name, 'is_supplier': False, 'is_manufacturer': True})

            if manufacturer_pk and pd.notna(row[f'MPN{i}']):
                manufacturer_part_pk = resolve_entity(api, ManufacturerPart, {
                    'part': part_manufacturer_pks[i-1],
                    'manufacturer': manufacturer_pk,
                    'MPN': row[f'MPN{i}']
                })

                if pd.notna(supplier_name):  # Check for non-empty supplier
                    supplier_pk = resolve_entity(api, Company, {'name': supplier_name, 'is_supplier': True, 'is_manufacturer': False})
                    if supplier_pk and pd.notna(row[f'SPN{i}']):
                        # Ensure part_manufacturer_pks has enough entries
                        if len(part_manufacturer_pks) >= i:
                            resolve_entity(api, SupplierPart, {
                                'part': part_manufacturer_pks[i - 1],
                                'supplier': supplier_pk,
                                'SKU': row[f'SPN{i}'],
                            })

    except Exception as e:
        logger.error(f"Error processing suppliers and manufacturers: {e}")

    logger.info(f"Processed row successfully: {row['NAME']}")

def process_csv_file(api: InvenTreeAPI, filename: str):
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