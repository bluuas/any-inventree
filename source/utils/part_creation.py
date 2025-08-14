"""
Functions for creating categories, parts, parameters, suppliers, manufacturers, and stock locations.
"""
import logging
from utils.logging_utils import get_configured_level
import pandas as pd
from inventree.api import InvenTreeAPI
from inventree.base import Attachment
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part, Parameter, ParameterTemplate, PartRelated
from inventree.stock import StockItem
from .entity_resolver import resolve_entity
from .relation_utils import add_pending_relation
from .error_codes import ErrorCodes
from .config import get_site_url

logger = logging.getLogger('part-creation')
logger.setLevel(get_configured_level() if callable(get_configured_level) else logging.INFO)

def create_part(api: InvenTreeAPI, row, category_pk):
    """
    Create a generic part and attach a datasheet.
    Returns (part_pk, error_code).
    """
    try:
        name = f"{row['NAME']}".strip()
        if not name or pd.isna(row['NAME']):
            logger.warning("Skipping row because 'NAME' is empty or NaN.")
            return None, ErrorCodes.INVALID_NAME
            
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
        
        if pk is None:
            logger.error(f"Failed to create part: {name}")
            return None, ErrorCodes.ENTITY_CREATION_FAILED
            
        # Update part link and IPN
        try:
            site_url = get_site_url()
            api.patch(url=f"part/{pk}/", data={'link': f"{site_url}/part/{pk}/"})
            
            designator = row['DESIGNATOR [str]'] if not pd.isna(row['DESIGNATOR [str]']) else ''
            rev0_pk = pk  # Placeholder for revision 0 part PK, TODO
            rev0_str = str(rev0_pk).zfill(6)
            api.patch(url=f"part/{pk}/", data={'IPN': f"{designator}{rev0_str}-{pk}"})
        except Exception as e:
            logger.warning(f"Failed to update part {pk} link or IPN: {e}")

        # Attach datasheet for specific parts, add link to itself for virtual parts
        try:
            datasheet_link = f"{site_url}/part/{pk}/" if is_virtual else row['DATASHEET_LINK'] if not pd.isna(row['DATASHEET_LINK']) else ''
            if datasheet_link:
                resolve_entity(api, Attachment, {
                    'link': datasheet_link,
                    'comment': 'datasheet',
                    'model_type': 'part',
                    'model_id': pk,
                })
        except Exception as e:
            logger.warning(f"Failed to create attachment for part {pk}: {e}")

        # get the part relations from RELATEDPART1,RELATEDPART2,RELATEDPART3
        try:
            for i in range(1, 4):
                related_part = row.get(f'RELATEDPART{i}')
                if pd.notna(related_part) and related_part != '':
                    add_pending_relation(pk, related_part)
        except Exception as e:
            logger.warning(f"Failed to add pending relations for part {pk}: {e}")
            
        return pk, ErrorCodes.SUCCESS
        
    except Exception as e:
        logger.error(f"Unexpected error creating part: {e}")
        return None, ErrorCodes.API_ERROR

# --- Parameters ---
def create_parameters(api: InvenTreeAPI, row, pk):
    """
    Create parameters for generic and specific parts from a CSV row.
    Returns error code.
    """
    try:
        description_index = row.index.get_loc('DESCRIPTION')
        manufacturer_index = row.index.get_loc('MANUFACTURER')
        parameters = [
            (row.index[i])
            for i in range(description_index + 1, manufacturer_index)
            if not pd.isna(row.index[i])
        ]

        if not parameters:
            logger.warning("No valid parameters found between 'DESCRIPTION' and 'MANUFACTURER'.")
            return ErrorCodes.SUCCESS

        for parameter in parameters:
            try:
                # Split parameter into name and unit if unit is present in square brackets
                if '[' in parameter and ']' in parameter:
                    parameter_name = parameter.split('[')[0].strip()
                    parameter_unit = parameter.split('[')[1].replace(']', '').strip()
                else:
                    parameter_name = parameter.strip()
                    parameter_unit = ''

                if pd.isna(parameter_name) or not parameter_name:
                    logger.warning(f"Parameter name '{parameter}' is invalid. Skipping.")
                    continue
                    
                parameter_template_pk = resolve_entity(api, ParameterTemplate, {
                    'name': parameter_name,
                })
                if parameter_template_pk is None:
                    logger.error(f"Parameter template not found for '{parameter_name}'. Skipping.")
                    continue

                parameter_value = row[parameter]
                # If parameter_value is NaN, replace with a dash
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
                logger.error(f"Error processing parameter '{parameter}': {e}")
                continue
                
        return ErrorCodes.SUCCESS

    except Exception as e:
        logger.error(f"Error processing parameters for part {pk}: {e}")
        return ErrorCodes.PARAMETER_ERROR

# --- Suppliers and Manufacturers ---
def create_suppliers_and_manufacturers(api: InvenTreeAPI, row, part_pk, stock_location_pk):
    """
    Create suppliers, manufacturers, and stock items for specific parts.
    Returns error code.
    """
    try:
        manufacturer_name = row.get('MANUFACTURER')
        mpn = row.get('MPN')

        if pd.isna(manufacturer_name):
            logger.debug("Skipping manufacturer or supplier because it is empty")
            return ErrorCodes.SUCCESS
            
        manufacturer_pk = resolve_entity(api, Company, {
            'name': manufacturer_name, 
            'is_supplier': False, 
            'is_manufacturer': True
        })
        
        if not manufacturer_pk:
            logger.error(f"Failed to create or find manufacturer: {manufacturer_name}")
            return ErrorCodes.SUPPLIER_ERROR
            
        if manufacturer_pk and mpn and pd.notna(mpn):
            try:
                resolve_entity(api, ManufacturerPart, {
                    'part': part_pk,
                    'manufacturer': manufacturer_pk,
                    'MPN': mpn
                })
            except Exception as e:
                logger.error(f"Failed to create manufacturer part: {e}")
                return ErrorCodes.SUPPLIER_ERROR
                
            # Dynamically get all suppliers by checking columns that start with 'SUPPLIER' followed by a number
            supplier_cols = [col for col in row.index if col.startswith('SUPPLIER') and col[len('SUPPLIER'):].isdigit()]
            for supplier_col in supplier_cols:
                try:
                    i = supplier_col[len('SUPPLIER'):]
                    supplier_name = row[supplier_col]
                    if pd.isna(supplier_name):
                        logger.debug(f"Skipping supplier {i} because it is empty")
                        continue

                    supplier_pk = resolve_entity(api, Company, {
                        'name': supplier_name, 
                        'is_supplier': True, 
                        'is_manufacturer': False
                    })
                    
                    if not supplier_pk:
                        logger.warning(f"Failed to create or find supplier: {supplier_name}")
                        continue

                    supplier_part_pk = resolve_entity(api, SupplierPart, {
                        'part': part_pk,
                        'supplier': supplier_pk,
                        'SKU': row.get(f'SKU{i}', None),
                    })
                    
                    if not supplier_part_pk:
                        logger.warning(f"Failed to create supplier part for supplier {supplier_name}")
                        
                except Exception as e:
                    logger.error(f"Error processing supplier {supplier_col}: {e}")
                    continue
                    
        return ErrorCodes.SUCCESS
        
    except Exception as e:
        logger.error(f"Error processing suppliers and manufacturers: {e}")
        return ErrorCodes.SUPPLIER_ERROR
