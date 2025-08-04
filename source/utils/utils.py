import os
import pandas as pd
from inventree.api import InvenTreeAPI
from inventree.base import Attachment
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part, Parameter, ParameterTemplate, PartRelated, BomItem
from inventree.stock import StockItem, StockLocation
import requests

import logging
logger = logging.getLogger(__name__)


INVENTREE_SITE_URL = os.getenv("INVENTREE_SITE_URL", "http://inventree.localhost")
KICAD_PLUGIN_PK = "kicad-library-plugin"

# Caches for entities to speed up lookups
caches = {
    Attachment: {},
    BomItem: {},
    Company: {},
    ManufacturerPart: {},
    Parameter: {},
    ParameterTemplate: {},
    Part: {},
    PartCategory: {},
    PartRelated: {},
    StockItem: {},
    StockLocation: {},
    SupplierPart: {},
}

# Lookup Table for identifiers per entity type
IDENTIFIER_LUT = {
    Attachment: ['filename', 'model_id'],
    BomItem: ['part', 'sub_part'],
    Company: ['name'],
    ManufacturerPart: ['MPN'],
    Parameter: ['part', 'template'],
    ParameterTemplate: ['name'],
    Part: ['name', 'category'],
    PartCategory: ['name', 'parent'],
    PartRelated: ['part_1', 'part_2'],
    StockItem: ['part', 'supplier_part'],
    StockLocation: ['name'],
    SupplierPart: ['SKU'],
}

def resolve_entity(api: InvenTreeAPI, entity_type, data):
    identifiers = IDENTIFIER_LUT.get(entity_type, [])
    if not identifiers:
        logger.error(f"No identifiers found for entity type: {entity_type.__name__}")
        return None

    try:
        cache = caches[entity_type]
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
        new_entity = entity_type.create(api, data)
        logger.debug(f"{entity_type.__name__} '{composite_key}' created successfully at ID: {new_entity.pk}")
        cache[composite_key] = new_entity.pk
        return new_entity.pk

    except Exception as e:
        logger.error(f"Error resolving entity for {entity_type.__name__} '{composite_key}': {e}")
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

def create_default_stock_location(api):
    try:
        return resolve_entity(api, StockLocation, {
            'name': 'Default',
            'description': 'Default stock location for all parts'
        })
    except Exception as e:
        logger.error(f"Error creating default stock location: {e}")
        return

def create_categories(api: InvenTreeAPI, row: pd.Series):
    part_category_pk = resolve_entity(api, PartCategory, {'name': row['CATEGORY'], 'parent': None, 'structural': True})
    part_subcategory_pk = resolve_entity(api, PartCategory, {'name': row['SUBCATEGORY'], 'parent': part_category_pk, 'structural':True})

    part_subcategory_generic_pk = resolve_entity(api, PartCategory, {'name': 'generic', 'parent': part_subcategory_pk})
    # part_subcategory_critical_pk = resolve_entity(api, PartCategory, {'name': 'critical', 'parent': part_subcategory_pk})
    part_subcategory_specific_pk = resolve_entity(api, PartCategory, {'name':'specific', 'parent': part_subcategory_pk})

    return part_subcategory_generic_pk, part_subcategory_specific_pk

def add_generic_category_to_kicad_plugin(api, part_subcategory_generic_pk):
    try:
        HEADERS = {
            "Authorization": f"Token {api.token}",
            "Content-Type": "application/json"
        }
        response = requests.post(f"{INVENTREE_SITE_URL}/plugin/{KICAD_PLUGIN_PK}/api/category/", headers=HEADERS, json={'category': part_subcategory_generic_pk})
        logger.debug(f"Adding generic part category to KiCAD plugin: {response.json()}")
    except Exception as e:
        logger.error(f"Error adding generic part category to KiCAD plugin: {e}")

def create_generic_part(api, row, part_subcategory_generic_pk):
    part_name_generic = f"{row['NAME']}_generic"
    part_description = row['DESCRIPTION'] if not pd.isna(row['DESCRIPTION']) else ''

    part_generic_pk = resolve_entity(api, Part, {
        'name': part_name_generic,
        'category': part_subcategory_generic_pk,
        'description': part_description,
        'virtual': True,
    })
    api.patch(url=f"part/{part_generic_pk}/", data={'link': f"{INVENTREE_SITE_URL}/part/{part_generic_pk}/"})
    api.post(url="attachment/", data={
        'link': f"{INVENTREE_SITE_URL}/part/{part_generic_pk}/",
        'comment': 'datasheet',
        'model_type': 'part',
        'model_id': part_generic_pk,
    })
    return part_generic_pk

def create_specific_parts(api, row, part_generic_pk, part_subcategory_specific_pk):
    part_specific_pks = []
    for i in range(1, 4):
        manufacturer_name = row[f'MANUFACTURER{i}']
        if pd.notna(manufacturer_name):
            part_name_manufacturer = f"{row['NAME']}_{manufacturer_name}_{row[f'MPN{i}']}".replace(" ", "_")
            part_specific_pk = resolve_entity(api, Part, {
                'name': part_name_manufacturer,
                'category': part_subcategory_specific_pk,
                'description': row['DESCRIPTION'],
                'link': row[f'DSLINK{i}']
            })
            part_specific_pks.append(part_specific_pk)

            resolve_entity(api, PartRelated, {
                'part_1': part_generic_pk,
                'part_2': part_specific_pk,
            })

            api.post(url="attachment/", data={
                'link': row[f'DSLINK{i}'],
                'comment': 'datasheet',
                'model_type': 'part',
                'model_id': part_specific_pk,
            })
    return part_specific_pks


def create_parameters(api, row, part_generic_pk, part_specific_pks):
    try:
        description_index = row.index.get_loc('DESCRIPTION')
        manufacturer1_index = row.index.get_loc('MANUFACTURER1')
        parameters = [row.iloc[i] for i in range(description_index + 1, manufacturer1_index) if not pd.isna(row.iloc[i])]
        logger.debug(f"Parameters: {parameters}")

        if not parameters:
            logger.warning("No valid parameters found between 'DESCRIPTION' and 'MANUFACTURER1'.")

        for i, parameter in enumerate(parameters):
            parameter_name = row.index[description_index + 1 + i]
            if pd.isna(parameter_name):
                logger.warning(f"Parameter name at index {description_index + 1 + i} is NaN. Skipping.")
                continue

            parameter_template_pk = resolve_entity(api, ParameterTemplate, {
                'name': parameter_name,
            })

            if parameter_template_pk is None:
                logger.error(f"Parameter template not found for '{parameter_name}'. Skipping.")
                continue

            for part_pk in [part_generic_pk] + part_specific_pks:
                resolve_entity(api, Parameter, {
                    'part': part_pk,
                    'template': parameter_template_pk,
                    'data': parameter
                })

        for i in range(1, 4):
            parameter_template_mpn_pk = resolve_entity(api, ParameterTemplate, {
                'name': f'MPN{i}',
            })
            mpn = row[f'MPN{i}']
            if mpn and pd.notna(mpn):
                resolve_entity(api, Parameter, {
                    'part': part_generic_pk,
                    'template': parameter_template_mpn_pk,
                    'data': mpn
                })
    except Exception as e:
        logger.error(f"Error processing parameters: {e}")

def create_suppliers_and_manufacturers(api, row, part_specific_pks, stock_location_pk):
    try:
        for i in range(1, 4):
            manufacturer_name = row[f'MANUFACTURER{i}']
            mpn = row[f'MPN{i}']
            supplier_name = row[f'SUPPLIER{i}']

            if pd.isna(manufacturer_name):
                logger.debug(f"Skipping manufacturer or supplier because it is empty")
                continue

            manufacturer_pk = resolve_entity(api, Company, {'name': manufacturer_name, 'is_supplier': False, 'is_manufacturer': True})

            if manufacturer_pk and mpn and pd.notna(mpn):
                manufacturer_part_pk = resolve_entity(api, ManufacturerPart, {
                    'part': part_specific_pks[i-1],
                    'manufacturer': manufacturer_pk,
                    'MPN': mpn
                })
                parameter_template_pk = resolve_entity(api, ParameterTemplate, {
                    'name': 'MPN'
                })
                resolve_entity(api, Parameter, {
                    'part': part_specific_pks[i-1],
                    'template': parameter_template_pk,
                    'data': mpn
                })

                if pd.notna(supplier_name):
                    supplier_pk = resolve_entity(api, Company, {'name': supplier_name, 'is_supplier': True, 'is_manufacturer': False})
                    if supplier_pk and pd.notna(row[f'SPN{i}']):
                        if len(part_specific_pks) >= i:
                            supplier_part = resolve_entity(api, SupplierPart, {
                                'part': part_specific_pks[i - 1],
                                'supplier': supplier_pk,
                                'SKU': row[f'SPN{i}'],
                            })
                            stock_pk = resolve_entity(api, StockItem, {
                                'part': part_specific_pks[i - 1],
                                'supplier_part': supplier_part,
                                'quantity': 10000,
                                'location': stock_location_pk,
                            })
    except Exception as e:
        logger.error(f"Error processing suppliers and manufacturers: {e}")


def process_csv_file(api: InvenTreeAPI, filename: str):
    try:
        df = pd.read_csv(filename).iloc[1:]  # Drop the 2nd row with the Units
        logger.info(f"Processing {df.shape[0]} row(s) from {filename}")
        for _, row in df.iterrows():
                # --------------------- Default Stock Location for Parts --------------------- #
                stock_location_pk = create_default_stock_location(api)
                # ----------------------- Categories and Subcategories ----------------------- #
                part_subcategory_generic_pk, part_subcategory_specific_pk = create_categories(api, row)
                add_generic_category_to_kicad_plugin(api, part_subcategory_generic_pk)
                # ----------------------------------- Parts ---------------------------------- #
                part_generic_pk = create_generic_part(api, row, part_subcategory_generic_pk)
                part_specific_pks = create_specific_parts(api, row, part_generic_pk, part_subcategory_specific_pk)
                # -------------------------------- Parameters -------------------------------- #
                create_parameters(api, row, part_generic_pk, part_specific_pks)
                # ------------------------ Suppliers and Manufacturers ----------------------- #
                create_suppliers_and_manufacturers(api, row, part_specific_pks, stock_location_pk)

                logger.info(f"Processed row successfully: {row['NAME']}")                 
    except Exception as e:
        logger.error(f"Error processing '{filename}': {e}")