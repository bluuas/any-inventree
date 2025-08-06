"""
Functions for creating categories, parts, parameters, suppliers, manufacturers, and stock locations.
"""
import logging
import pandas as pd
from inventree.api import InvenTreeAPI
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part, Parameter, ParameterTemplate, PartRelated
from inventree.stock import StockItem, StockLocation
from .entity_resolver import resolve_entity

logger = logging.getLogger('InvenTreeCLI')

# --- Stock Location ---
def create_default_stock_location(api: InvenTreeAPI):
    """Create or get the default stock location."""
    try:
        return resolve_entity(api, StockLocation, {
            'name': 'Default',
            'description': 'Default stock location for all parts'
        })
    except Exception as e:
        logger.error(f"Error creating default stock location: {e}")
        return

# --- Parts ---
def create_generic_part(api: InvenTreeAPI, row, part_subcategory_generic_pk, site_url):
    """Create a generic part and attach a datasheet."""
    part_name_generic = f"{row['NAME']}_generic"
    part_description = row['DESCRIPTION'] if not pd.isna(row['DESCRIPTION']) else ''
    part_generic_pk = resolve_entity(api, Part, {
        'name': part_name_generic,
        'category': part_subcategory_generic_pk,
        'description': part_description,
        'virtual': True,
        'revision': '0',
    })
    api.patch(url=f"part/{part_generic_pk}/", data={'link': f"{site_url}/part/{part_generic_pk}/"})
    api.post(url="attachment/", data={
        'link': f"{site_url}/part/{part_generic_pk}/",
        'comment': 'datasheet',
        'model_type': 'part',
        'model_id': part_generic_pk,
    })
    return part_generic_pk

def create_specific_parts(api: InvenTreeAPI, row, part_generic_pk, part_subcategory_specific_pk):
    """Create specific parts for each manufacturer in the row."""
    part_specific_pks = []
    for i in range(1, 4):
        manufacturer_name = row[f'MANUFACTURER{i}']
        if pd.notna(manufacturer_name):
            part_name_manufacturer = f"{row['NAME']}_{manufacturer_name}_{row[f'MPN{i}']}".replace(" ", "_")
            part_specific_pk = resolve_entity(api, Part, {
                'name': part_name_manufacturer,
                'category': part_subcategory_specific_pk,
                'description': row['DESCRIPTION'],
                'link': row[f'DSLINK{i}'],
                'revision': '0',
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

# --- Parameters ---
def create_parameters(api: InvenTreeAPI, row, part_generic_pk, part_specific_pks):
    """Create parameters for generic and specific parts from a CSV row."""
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

# --- Suppliers and Manufacturers ---
def create_suppliers_and_manufacturers(api: InvenTreeAPI, row, part_specific_pks, stock_location_pk):
    """Create suppliers, manufacturers, and stock items for specific parts."""
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
