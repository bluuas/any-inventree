import pandas as pd
import os
import logging
from .config import get_site_url
from .error_codes import ErrorCodes

from inventree.api import InvenTreeAPI
from inventree.company import ManufacturerPart
from inventree.part import Part, Parameter, PartRelated

logger = logging.getLogger('InvenTreeCLI')

class CsvEntity:
    """
    Represents a CSV entity with a primary key. Used to mimic a return value from an InvenTree API .create() call. 
    """
    def __init__(self, pk):
        self.pk = pk

class CsvDbWriter:
    CSV_DB_WRITER_IS_ACTIVE = True

    @classmethod
    def get_status(cls):
        return cls.CSV_DB_WRITER_IS_ACTIVE

    DB_PART_COLUMNS = [
        "id","name","description","keywords","IPN","link","image","minimum_stock","units","trackable","purchaseable","salable","active","notes",
        "bom_checksum","bom_checked_date","bom_checked_by_id","category_id","default_location_id","default_supplier_id","is_template","variant_of_id",
        "assembly","component","virtual","revision","creation_date","creation_user_id","level","lft","rght","tree_id","default_expiry","base_cost",
        "multiple","metadata","barcode_data","barcode_hash","last_stocktake","responsible_owner_id","locked","revision_of_id","testable"
    ]
    DB_PARTPARAMETER_COLUMNS = [
        "id","data","part_id","template_id","data_numeric","metadata"
    ]
    DB_PARTRELATED_COLUMNS = [
        "id","part_1_id","part_2_id","metadata","note"
    ]
    DB_MANUFACTURERPART_COLUMNS = [
        "id","MPN","link","description","manufacturer_id","part_id","metadata","barcode_data","barcode_hash","notes","name","keywords","ipn","image","minimum_stock","units","trackable","purchaseable","salable","active","bom_checksum","bom_checked_date","bom_checked_by_id","category_id","default_location_id","default_supplier_id","is_template","variant_of_id","assembly","component","virtual","revision","creation_date","creation_user_id","level","lft","rght","tree_id","default_expiry","base_cost","multiple","last_stocktake","responsible_owner_id","locked","revision_of_id","testable"
    ]
    DB_PART_ROWS = []
    DB_PARTPARAMETER_ROWS = []
    DB_PARTRELATED_ROWS = []
    DB_MANUFACTURERPART_ROWS = []


    ID_UPPER_LIMIT = {
        "part": 0,
        "partparameter": 0,
        "partrelated": 0,
        "manufacturerpart": 0,
    }

    @classmethod
    def fetch_id_counters(cls, api: InvenTreeAPI):
            parts = Part.list(api)
            upper = max((part['pk'] for part in parts), default=None)
            if upper is not None:
                cls.ID_UPPER_LIMIT["part"] = upper

            parameters = Parameter.list(api)
            upper = max((param['pk'] for param in parameters), default=None)
            if upper is not None:
                cls.ID_UPPER_LIMIT["partparameter"] = upper

            related = PartRelated.list(api)
            upper = max((rel['pk'] for rel in related), default=None)
            if upper is not None:
                cls.ID_UPPER_LIMIT["partrelated"] = upper

            manufacturers = ManufacturerPart.list(api)
            upper = max((man['pk'] for man in manufacturers), default=None)
            if upper is not None:
                cls.ID_UPPER_LIMIT["manufacturerpart"] = upper

    @classmethod
    def get_next_id(cls, key):
        cls.ID_UPPER_LIMIT[key] += 1
        return cls.ID_UPPER_LIMIT[key] - 1

    @classmethod
    def write_df_to_csv(cls, df, columns, filename):
        output_dir = os.path.join(os.path.dirname(__file__), "../csv-output")
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
        if not df.empty:
            df = df[columns]
            df.to_csv(output_path, mode='w', header=True, index=False, sep=',')
            logger.info(f"Written DataFrame to CSV: {output_path}")
        else:
            logger.warning(f"DataFrame is empty. No CSV written: {output_path}")

    @classmethod
    def write_all_db_csv(cls):
        cls.write_df_to_csv(pd.DataFrame(cls.DB_PART_ROWS), cls.DB_PART_COLUMNS, "part_part.csv")
        cls.write_df_to_csv(pd.DataFrame(cls.DB_PARTPARAMETER_ROWS), cls.DB_PARTPARAMETER_COLUMNS, "part_partparameter.csv")
        cls.write_df_to_csv(pd.DataFrame(cls.DB_PARTRELATED_ROWS), cls.DB_PARTRELATED_COLUMNS, "part_partrelated.csv")
        cls.write_df_to_csv(pd.DataFrame(cls.DB_MANUFACTURERPART_ROWS), cls.DB_MANUFACTURERPART_COLUMNS, "company_manufacturerpart.csv")

    @classmethod
    def add_part_row_db(cls, data):
        id = cls.get_next_id("part")
        category_pk = data.get("category", "")
        name = data.get("name", "")
        description = data.get("description", "")
        link = f"{get_site_url()}/part/{id}/"
        minimum_stock = data.get("minimum_stock", "0")
        revision = data.get("revision", "0")
        notes = data.get("notes", "")
        is_virtual = str(data.get("type", "")).strip().lower() in ['generic', 'critical']
        designator = data.get('designator [str]', '')
        rev0_str = str(id).zfill(6)
        ipn = f"{designator}{rev0_str}-{id}"

        out_row = {
            "id": id,
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
            "lft": str(id),
            "rght": str(id+1),
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
        cls.DB_PART_ROWS.append(out_row)
        return id

    @classmethod
    def add_partparameter_db(cls, part_pk, parameter_template_pk, display_value, numeric_value):
        out_row = {
            "id": cls.get_next_id("partparameter"),
            "data": display_value,
            "part_id": part_pk,
            "template_id": parameter_template_pk,
            "data_numeric": numeric_value,
            "metadata": "{}"
        }
        cls.DB_PARTPARAMETER_ROWS.append(out_row)

    @classmethod
    def add_partrelated_row_db(cls, row, part_1_id, part_2_id):
        out_row = {
            "id": cls.get_next_id("partrelated"),
            "part_1_id": part_1_id,
            "part_2_id": part_2_id,
            "metadata": "{}",
            "note": row.get("NOTE", "")
        }
        cls.DB_PARTRELATED_ROWS.append(out_row)

    @classmethod
    def add_manufacturerpart_db(cls, row, part_pk, manufacturer_pk):
        id = cls.get_next_id("manufacturerpart")
        mpn = row.get("MPN", "")
        link = f"{get_site_url()}/company/manufacturer-part/{id}/"
        description = row.get("DESCRIPTION", "")
        notes = row.get("NOTES", "")
        minimum_stock = row.get("MINIMUM_STOCK", "0")
        is_virtual = str(row.get("TYPE", "")).strip().lower() in ['generic', 'critical']
        designator = row.get('DESIGNATOR [str]', '')
        rev0_str = str(part_pk).zfill(6)
        ipn = f"{designator}{rev0_str}-{part_pk}"

        out_row = {
            "id": id,
            "MPN": mpn,
            "link": link,
            "description": description,
            "manufacturer_id": manufacturer_pk,
            "part_id": part_pk,
            "metadata": "{}",
            "barcode_data": "",
            "barcode_hash": "",
            "notes": notes,
            "name": row.get("NAME", ""),
            "keywords": "",
            "ipn": ipn,
            "image": "",
            "minimum_stock": minimum_stock,
            "units": "",
            "trackable": "false",
            "purchaseable": "true",
            "salable": "false",
            "active": "true",
            "bom_checksum": "",
            "bom_checked_date": "",
            "bom_checked_by_id": "",
            "category_id": "",
            "default_location_id": "",
            "default_supplier_id": "",
            "is_template": "false",
            "variant_of_id": "",
            "assembly": "false",
            "component": "false",
            "virtual": str(is_virtual).lower(),
            "revision": row.get("REVISION", "0"),
            "creation_date": "2025-09-04",
            "creation_user_id": "1",
            "level": "0",
            "lft": str(part_pk),
            "rght": str(part_pk+1),
            "tree_id": "1",
            "default_expiry": "0",
            "base_cost": "0.000000",
            "multiple": "1",
            "last_stocktake": "",
            "responsible_owner_id": "",
            "locked": "false",
            "revision_of_id": "",
        }
        cls.DB_MANUFACTURERPART_ROWS.append(out_row)

    @classmethod
    def create(cls, entity_type, data) -> tuple:
        """
        Create a CSV row for the given entity_type and data, return an object with .pk attribute.
        """
        if entity_type.__name__ == "Part":
            pk = cls.add_part_row_db(data)
            return CsvEntity(pk), ErrorCodes.SUCCESS
        elif entity_type.__name__ == "Parameter":
            part_pk = data.get("part", "")
            template_pk = data.get("template", "")
            display_value = data.get("data", "")
            numeric_value = data.get("data_numeric", "")
            cls.add_partparameter_db(part_pk, template_pk, display_value, numeric_value)
            return CsvEntity(None), ErrorCodes.SUCCESS
        elif entity_type.__name__ == "PartRelated":
            part_1_id = data.get("part_1", "")
            part_2_id = data.get("part_2", "")
            cls.add_partrelated_row_db(data, part_1_id, part_2_id)
            return CsvEntity(None), ErrorCodes.SUCCESS
        elif entity_type.__name__ == "ManufacturerPart":
            part_pk = data.get("part", "")
            manufacturer_pk = data.get("manufacturer", "")
            cls.add_manufacturerpart_db(data, part_pk, manufacturer_pk)
            return CsvEntity(None), ErrorCodes.SUCCESS
        # Add more entity types as needed
        else:
            logger.warning(f"CsvDbWriter.create: Unsupported entity type {entity_type.__name__}")
            return CsvEntity(None), ErrorCodes.ENTITY_CREATION_FAILED