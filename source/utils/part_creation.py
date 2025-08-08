"""
Functions for creating categories, parts, parameters, suppliers, manufacturers, and stock locations.
"""
import logging
from utils.logging_utils import get_configured_level
import pandas as pd
from inventree.api import InvenTreeAPI
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part, Parameter, ParameterTemplate, PartRelated
from inventree.stock import StockItem
from .entity_resolver import resolve_entity
from .relation_utils import add_pending_relation

logger = logging.getLogger('part-creation')
logger.setLevel(get_configured_level() if callable(get_configured_level) else logging.INFO)

def create_part(api: InvenTreeAPI, row, category_pk, site_url):
    """Create a generic part and attach a datasheet."""
    name = f"{row['NAME']}"
    description = row['DESCRIPTION'] if not pd.isna(row['DESCRIPTION']) else ''
    is_virtual = str(row['TYPE']).strip().lower() in ['generic', 'critical']
    revision = row['REVISION'] if not pd.isna(row['REVISION']) else '0'

    pk = resolve_entity(api, Part, {
        'name': name,
        'category': category_pk,
        'description': description,
        'virtual': is_virtual,
        'revision': revision,
    })
    api.patch(url=f"part/{pk}/", data={'link': f"{site_url}/part/{pk}/"})

    # Patch again and update the IPN
    designator = row['DESIGNATOR [str]'] if not pd.isna(row['DESIGNATOR [str]']) else ''
    rev0_pk = pk  # Placeholder for revision 0 part PK, TODO
    rev0_str = str(rev0_pk).zfill(6)
    api.patch(url=f"part/{pk}/", data={'IPN': f"{designator}{rev0_str}-{pk}"})

    # Attach datasheet for specific parts, add link to itself for virtual parts
    datasheet_link = f"{site_url}/part/{pk}/" if is_virtual else row['DSLINK']
    api.post(url="attachment/", data={
        'link': datasheet_link,
        'comment': 'datasheet',
        'model_type': 'part',
        'model_id': pk,
    })

    # get the part relations from RELATEDPART1,RELATEDPART2,RELATEDPART3
    for i in range(1, 4):
        related_part = row.get(f'RELATEDPART{i}')
        if pd.notna(related_part) and related_part != '':
            add_pending_relation(pk, related_part)
    return pk

# --- Parameters ---
def create_parameters(api: InvenTreeAPI, row, pk):
    """Create parameters for generic and specific parts from a CSV row."""
    try:
        description_index = row.index.get_loc('DESCRIPTION')
        manufacturer_index = row.index.get_loc('MANUFACTURER')
        parameters = [
            (row.index[i])
            for i in range(description_index + 1, manufacturer_index)
            if not pd.isna(row.index[i])
        ]

        if not parameters:
            logger.warning("No valid parameters found between 'DESCRIPTION' and 'MANUFACTURER1'.")

        for parameter in parameters:
            # Split parameter into name and unit if unit is present in square brackets
            if '[' in parameter and ']' in parameter:
                parameter_name = parameter.split('[')[0].strip()
                parameter_unit = parameter.split('[')[1].replace(']', '').strip()
            else:
                parameter_name = parameter.strip()
                parameter_unit = ''

            if pd.isna(parameter_name):
                logger.warning(f"Parameter name at index {description_index + 1 + i} is NaN. Skipping.")
                # continue
            parameter_template_pk = resolve_entity(api, ParameterTemplate, {
                'name': parameter_name,
            })
            if parameter_template_pk is None:
                logger.error(f"Parameter template not found for '{parameter_name}'. Skipping.")
                # continue

            parameter_value = row[parameter]
            # If parameter_value is NaN, replace with a whitespace
            if pd.isna(parameter_value):
                parameter_value = '-'
            # If parameter_value is a string and contains the unit, strip it
            elif isinstance(parameter_value, str) and parameter_unit and parameter_value.endswith(parameter_unit):
                parameter_value = parameter_value[: -len(parameter_unit)].strip()

            resolve_entity(api, Parameter, {
                'part': pk,
                'template': parameter_template_pk,
                'data': parameter_value,
                'data_numeric': parameter_value if isinstance(parameter_value, (int, float)) else None,
            })

    except Exception as e:
        logger.error(f"Error processing parameters: {e}")
        quit()

# --- Suppliers and Manufacturers ---
def create_suppliers_and_manufacturers(api: InvenTreeAPI, row, part_pk, stock_location_pk):
    """Create suppliers, manufacturers, and stock items for specific parts."""
    try:
        manufacturer_name = row[f'MANUFACTURER']
        mpn = row[f'MPN']

        if pd.isna(manufacturer_name):
            logger.debug(f"Skipping manufacturer or supplier because it is empty")
            return
        manufacturer_pk = resolve_entity(api, Company, {'name': manufacturer_name, 'is_supplier': False, 'is_manufacturer': True})
        if manufacturer_pk and mpn and pd.notna(mpn):
            resolve_entity(api, ManufacturerPart, {
                'part': part_pk,
                'manufacturer': manufacturer_pk,
                'MPN': mpn
            })
            # Dynamically get all suppliers by checking columns that start with 'SUPPLIER' followed by a number
            supplier_cols = [col for col in row.index if col.startswith('SUPPLIER') and col[len('SUPPLIER'):].isdigit()]
            for supplier_col in supplier_cols:
                i = supplier_col[len('SUPPLIER'):]
                supplier_name = row[supplier_col]
                if pd.isna(supplier_name):
                    logger.debug(f"Skipping supplier {i} because it is empty")
                    continue

                supplier_pk = resolve_entity(api, Company, {'name': supplier_name, 'is_supplier': True, 'is_manufacturer': False})

                supplier_part_pk = resolve_entity(api, SupplierPart, {
                    'part': part_pk,
                    'supplier': supplier_pk,
                    'SKU': row.get(f'SKU{i}', None),
                })
                # resolve_entity(api, StockItem, {
                #     'part': part_pk,
                #     'supplier_part': supplier_part_pk,
                #     'quantity': 10000,
                #     'location': stock_location_pk,
                # })
    except Exception as e:
        logger.error(f"Error processing suppliers and manufacturers: {e}")
