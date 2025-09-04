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
import os

logger = logging.getLogger('InvenTreeCLI')
logger.setLevel(get_configured_level() if callable(get_configured_level) else logging.INFO)
# Accumulate part rows here
PART_ROWS = []

def load_existing_part_pks():
    """
    Load existing PKs from the output CSV file to avoid duplicates.
    """
    output_path = os.path.join(os.path.dirname(__file__), "../csv-output/part_part.csv")
    output_path = os.path.abspath(output_path)
    if os.path.exists(output_path):
        try:
            df_existing = pd.read_csv(output_path, usecols=["PK"])
            return set(df_existing["PK"].astype(str))
        except Exception as e:
            logger.warning(f"Failed to load existing PKs from CSV: {e}")
            return set()
    return set()

EXISTING_PART_PKS = load_existing_part_pks()

def add_part_row(api, row, pk):
    """
    Add part data to the global PART_ROWS list if PK doesn't exist yet (including CSV file).
    """
    pk_str = str(pk)
    if pk_str in EXISTING_PART_PKS:
        return  # PK already exists, do not append
    category_str = row.get("CATEGORY", "")
    type_str = str(row.get("TYPE", "")).strip()
    if type_str:
        category_str = f"{category_str}/{type_str}"
    category_pk, _ = resolve_category_string(api, category_str)
    out_row = {
        "PK": pk,
        "Minimum Stock": row.get("MINIMUM_STOCK", "0"),
        "Name": row.get("NAME", ""),
        "Category": category_pk,
        "Description": row.get("DESCRIPTION", ""),
        "IPN": "",  # Will be set below
        "Link": f"{get_site_url()}/part/{pk}/",
        "Notes": row.get("NOTES", ""),
        "Revision": row.get("REVISION", ""),
        "Virtual": str(row.get("TYPE", "")).strip().lower() in ['generic', 'critical'],
    }
    designator = row.get('DESIGNATOR [str]', '')
    rev0_str = str(pk).zfill(6)
    out_row["IPN"] = f"{designator}{rev0_str}-{pk}"
    PART_ROWS.append(out_row)

DB_COLUMNS = [
    "id","name","description","keywords","IPN","link","image","minimum_stock","units","trackable","purchaseable","salable","active","notes",
    "bom_checksum","bom_checked_date","bom_checked_by_id","category_id","default_location_id","default_supplier_id","is_template","variant_of_id",
    "assembly","component","virtual","revision","creation_date","creation_user_id","level","lft","rght","tree_id","default_expiry","base_cost",
    "multiple","metadata","barcode_data","barcode_hash","last_stocktake","responsible_owner_id","locked","revision_of_id","testable"
]

def add_part_row_db(api, row, pk, category_pk):
    """
    Add part data to PART_ROWS for direct DB import CSV.
    """
    # Fill in fields from row or sensible defaults
    name = row.get("NAME", "")
    description = row.get("DESCRIPTION", "")
    link = f"{get_site_url()}/part/{pk}/"
    minimum_stock = row.get("MINIMUM_STOCK", "0")
    revision = row.get("REVISION", "0")
    notes = row.get("NOTES", "")
    is_virtual = str(row.get("TYPE", "")).strip().lower() in ['generic', 'critical']
    designator = row.get('DESIGNATOR [str]', '')
    rev0_str = str(pk).zfill(6)
    ipn = f"{designator}{rev0_str}-{pk}"

    # Fill in DB columns
    out_row = {
        "id": pk,
        "name": name,
        "description": description,
        "keywords": "",
        "IPN": ipn,
        "link": link,
        "image": "",
        "minimum_stock": minimum_stock,
        "units": "",
        "trackable": "false",
        "purchaseable": "true",
        "salable": "false",
        "active": "true",
        "notes": notes,
        "bom_checksum": "",
        "bom_checked_date": "",
        "bom_checked_by_id": "",
        "category_id": category_pk,
        "default_location_id": "",
        "default_supplier_id": "",
        "is_template": "false",
        "variant_of_id": "",
        "assembly": "false",
        "component": "false",
        "virtual": str(is_virtual).lower(),
        "revision": revision,
        "creation_date": "2025-09-04",
        "creation_user_id": "1",
        "level": "0",
        "lft": str(pk),
        "rght": str(pk+1),
        "tree_id": "1",
        "default_expiry": "0",
        "base_cost": "0.000000",
        "multiple": "1",
        "metadata": "{}",
        "barcode_data": "",
        "barcode_hash": "",
        "last_stocktake": "",
        "responsible_owner_id": "",
        "locked": "false",
        "revision_of_id": "",
        "testable": "false"
    }
    PART_ROWS.append(out_row)

def write_parts_df_to_csv():
    """
    Write all accumulated part rows to csv-output/part_part.csv using pandas.
    Output CSV columns: PK, Minimum Stock, Name, Category, Description, IPN, Link, Notes, Revision, Virtual
    """
    output_path = os.path.join(os.path.dirname(__file__), "../csv-output/part_part.csv")
    output_path = os.path.abspath(output_path)
    columns = [
        "PK",
        "Minimum Stock",
        "Name",
        "Category",
        "Description",
        "IPN",
        "Link",
        "Notes",
        "Revision",
        "Virtual"
    ]
    df = pd.DataFrame(PART_ROWS)
    # Only write if there are rows
    if not df.empty:
        df = df[columns]  # Ensure column order and only output specified columns
        df.to_csv(output_path, mode='w', header=True, index=True)

def write_parts_db_csv():
    """
    Write all accumulated part rows to csv-output/part_part.csv for DB import.
    """
    output_path = os.path.join(os.path.dirname(__file__), "../csv-output/part_part.csv")
    output_path = os.path.abspath(output_path)
    df = pd.DataFrame(PART_ROWS)
    if not df.empty:
        df = df[DB_COLUMNS]
        df.to_csv(output_path, mode='w', header=True, index=False, sep=',')

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

        if USE_API:
            pk = resolve_entity(api, Part, {
                'name': name,
                'category': category_pk,
                'description': description,
                'virtual': is_virtual,
                'revision': revision,
            })
        else:
            pk = get_next_pk()

        if pk is None:
            logger.error(f"Failed to create part: {name}")
            return None, ErrorCodes.ENTITY_CREATION_FAILED

        # Add to DataFrame buffer after part creation
        try:
            add_part_row_db(api, row, pk, category_pk)
        except Exception as e:
            logger.warning(f"Failed to buffer part {pk} for DB CSV: {e}")

        if USE_API:
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

        if USE_API:
            for param_col, param_name, param_unit in parsed_params:
                try:
                    parameter_template_pk = resolve_entity(api, ParameterTemplate, {'name': param_name})
                    if parameter_template_pk is None:
                        logger.error(f"Parameter template not found for '{param_name}' Unit: {param_unit}. Skipping.")
                        continue

                    raw_value = row[param_col]
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

USE_API = False  # Set to False to skip API calls and only generate CSV rows
START_PK = 1    # Set this to the initial PK index for bulk generation
CURRENT_HIGHEST_PK = START_PK

def set_bulk_mode(start_pk):
    global USE_API, START_PK, CURRENT_HIGHEST_PK
    USE_API = False
    START_PK = start_pk
    CURRENT_HIGHEST_PK = start_pk

def get_next_pk():
    global CURRENT_HIGHEST_PK
    pk = CURRENT_HIGHEST_PK
    CURRENT_HIGHEST_PK += 1
    return pk

def get_highest_part_pk(api):
    """
    Get the highest PK from all existing parts.
    """
    try:
        parts = Part.list(api)
        if not parts:
            return 0
        return max(part['pk'] for part in parts)
    except Exception as e:
        logger.warning(f"Could not determine highest part PK: {e}")
        return 0

def set_bulk_mode_from_api(api):
    """
    Set bulk mode and starting PK using the highest PK from the API.
    """
    highest_pk = get_highest_part_pk(api)
    set_bulk_mode(highest_pk + 1)
