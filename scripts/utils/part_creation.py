"""
Functions for creating categories, parts, parameters, suppliers, manufacturers, and stock locations.
"""
import logging
from utils.logging_utils import get_configured_level
import pandas as pd
from inventree.api import InvenTreeAPI
from inventree.base import Attachment
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import Part, Parameter, ParameterTemplate
from .entity_resolver import resolve_entity, resolve_category_string
from .relation_utils import add_pending_relation
from .error_codes import ErrorCodes
from .config import get_site_url
from .value_parser import parse_parameter_value

logger = logging.getLogger('InvenTreeCLI')
logger.setLevel(get_configured_level() if callable(get_configured_level) else logging.INFO)

def create_part(api: InvenTreeAPI, row, category_pk):
    """
    Create a generic part and attach a datasheet.
    Returns (part_pk, error_code).
    """
    try:
        name = f"{row['NAME']}".strip()
        if not name or pd.isna(row['NAME']):
            return None, ErrorCodes.INVALID_NAME
            
        description = row['DESCRIPTION'] if not pd.isna(row['DESCRIPTION']) else ''
        is_virtual = str(row['TYPE']).strip().lower() in ['generic', 'critical']
        revision = row['REVISION'] if not pd.isna(row['REVISION']) else '0'
        # the designator is not an official field, but we use it for naming and the IPN
        designator = row['DESIGNATOR'] if 'DESIGNATOR' in row and not pd.isna(row['DESIGNATOR']) else ''

        pk = resolve_entity(api, Part, {
            'name': name,
            'category': category_pk,
            'description': description,
            'virtual': is_virtual,
            'revision': revision,
            'designator': designator
        })

        if pk is None:
            logger.error(f"Failed to create part: {name}")
            return None, ErrorCodes.ENTITY_CREATION_FAILED
        
        # Attach datasheet for specific parts, add link to itself for virtual parts
        try:
            site_url = get_site_url()
            datasheet_link = f"{site_url}/part/{pk}/" if is_virtual else row['DATASHEET_LINK'] if not pd.isna(row['DATASHEET_LINK']) else ''
            revision = row['DATASHEET_REVISION'] if 'DATASHEET_REVISION' in row and not pd.isna(row['DATASHEET_REVISION']) else ''
            if datasheet_link:
                resolve_entity(api, Attachment, {
                    'link': datasheet_link,
                    'comment': 'datasheet',
                    'model_type': 'part',
                    'model_id': pk,
                })
        except Exception as e:
            logger.warning(f"Failed to create attachment for part {pk}: {e}")

        # # Update part link and IPN
        # try:
            
        #     api.patch(url=f"part/{pk}/", data={'link': f"{site_url}/part/{pk}/"})
        #     designator = row['DESIGNATOR [str]'] if not pd.isna(row['DESIGNATOR [str]']) else ''
        #     rev0_pk = pk  # Placeholder for revision 0 part PK, TODO
        #     rev0_str = str(rev0_pk).zfill(6)
        #     api.patch(url=f"part/{pk}/", data={'IPN': f"{designator}{rev0_str}-{pk}"})
        # except Exception as e:
        #     logger.warning(f"Failed to update part {pk} link or IPN: {e}")

        # get the part relations from RELATEDPARTS (comma separated string)
        try:
            related_parts_str = row.get('RELATEDPARTS')
            if pd.notna(related_parts_str) and related_parts_str:
                related_parts = [p.strip() for p in related_parts_str.split(',') if p.strip()]
                for related_part in related_parts:
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
        # NOTES is the last column of the part attributes. Everything after until MANUFACTURER is considered a parameter.
        notes_index = row.index.get_loc('NOTES')
        manufacturer_index = row.index.get_loc('MANUFACTURER')
        param_columns = row.index[notes_index + 1:manufacturer_index]

        # Pre-parse parameter names and units
        parsed_params = []
        for param_col in param_columns:
            if pd.isna(param_col) or not param_col.strip():
                continue
            if '[' in param_col and ']' in param_col:
                name = param_col.split('[')[0].strip()
                unit = param_col.split('[')[1].replace(']', '').strip()
            else:
                name = param_col.strip()
                unit = ''
            if not name:
                logger.warning(f"Parameter name '{param_col}' is invalid. Skipping.")
                continue
            parsed_params.append((param_col, name, unit))

        if not parsed_params:
            logger.warning("No valid parameters found between 'NOTES' and 'MANUFACTURER'.")
            return ErrorCodes.SUCCESS

        for param_col, param_name, param_unit in parsed_params:
            try:
                parameter_template_pk = resolve_entity(api, ParameterTemplate, {'name': param_name})
                if parameter_template_pk is None:
                    logger.error(f"Parameter template not found for '{param_name}' Unit: {param_unit}. Skipping.")
                    continue

                raw_value = row[param_col]
                if pd.isna(raw_value) or not str(raw_value).strip():
                    logger.debug(f"Skipping empty parameter '{param_col}' for part {pk}.")
                    continue
                logger.debug(f"Parsing value: {raw_value}, unit: {param_unit}")
                display_value, numeric_value = parse_parameter_value(raw_value, param_unit)
                logger.debug(f"Parsed value: display='{display_value}', numeric={numeric_value}")

                resolve_entity(api, Parameter, {
                    'part': pk,
                    'template': parameter_template_pk,
                    'data': display_value,
                    'data_numeric': numeric_value,
                })
            except Exception as e:
                logger.error(f"Error processing parameter '{param_col}': {e}")
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

            # Dynamically get all suppliers by checking columns that start with 'SUPPLIER' followed by a number, then followed by anything else
            # e.g. SUPPLIER1_NAME, SUPPLIER1_SKU, SUPPLIER1_STATUS
            import re
            supplier_pattern = re.compile(r'^SUPPLIER(\d+)_NAME$')
            supplier_cols = [col for col in row.index if supplier_pattern.match(col)]
            for supplier_col in supplier_cols:
                try:
                    match = supplier_pattern.match(supplier_col)
                    i = match.group(1) if match else ''
                    supplier_name = row[supplier_col]
                    if pd.isna(supplier_name) or not str(supplier_name).strip():
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

                    sku_col = f'SUPPLIER{i}_SKU'
                    sku = row.get(sku_col, None)
                    supplier_part_pk = resolve_entity(api, SupplierPart, {
                        'part': part_pk,
                        'supplier': supplier_pk,
                        'SKU': sku,
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
