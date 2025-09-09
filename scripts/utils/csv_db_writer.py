import pandas as pd
import os
import logging
from .config import get_site_url
from .error_codes import ErrorCodes
from .cache import entity_cache

from inventree.api import InvenTreeAPI
from inventree.base import Attachment
from inventree.company import ManufacturerPart, SupplierPart
from inventree.part import Part, Parameter, PartRelated

logger = logging.getLogger('InvenTreeCLI')

class CsvDbWriter:
    CSV_DB_WRITER_IS_ACTIVE = False
    _id_counters_fetched = False

    @classmethod
    def is_active(cls):
        return cls.CSV_DB_WRITER_IS_ACTIVE
    
    @classmethod
    def set_active(cls, active: bool):
        cls.CSV_DB_WRITER_IS_ACTIVE = active

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
        "id","MPN","link","description","manufacturer_id","part_id","metadata","barcode_data","barcode_hash","notes"
    ]
    DB_ATTACHMENT_COLUMNS = [
        "id","model_id","attachment","link","comment","upload_date","file_size","model_type","upload_user_id","metadata"
    ]
    DB_SUPPLIERPART_COLUMNS = [
        "id","SKU","link","description","note","base_cost","packaging","multiple","part_id","supplier_id","manufacturer_part_id","availability_updated","available","barcode_data","barcode_hash","updated","metadata","pack_quantity","pack_quantity_native","active","notes"
    ]
        
    DB_PART_ROWS = []
    DB_PARTPARAMETER_ROWS = []
    DB_PARTRELATED_ROWS = []
    DB_MANUFACTURERPART_ROWS = []
    DB_ATTACHMENT_ROWS = []
    DB_SUPPLIERPART_ROWS = []

    ID_UPPER_LIMIT = {
        "attachment": 0,
        "part": 0,
        "partparameter": 0,
        "partrelated": 0,
        "manufacturerpart": 0,
        "supplierpart": 0
    }

    @classmethod
    def fetch_id_counters(cls, api: InvenTreeAPI):
        logger.info("Fetching ID upper limits from cache...")
        if not entity_cache.get('part'):
            entity_cache.populate(api)

        parts = entity_cache.get('part', [])
        upper = max((part['pk'] for part in parts), default=None)
        if upper is not None:
            cls.ID_UPPER_LIMIT["part"] = upper

        parameters = entity_cache.get('parameter', [])
        upper = max((param['pk'] for param in parameters), default=None)
        if upper is not None:
            cls.ID_UPPER_LIMIT["partparameter"] = upper

        logger.debug("fetching related parts from cache...")
        related = entity_cache.get('partrelated', [])
        upper = max((rel['pk'] for rel in related), default=None)
        if upper is not None:
            cls.ID_UPPER_LIMIT["partrelated"] = upper

        logger.debug("fetching manufacturer parts from cache...")
        manufacturers = entity_cache.get('manufacturerpart', [])
        upper = max((man['pk'] for man in manufacturers), default=None)
        if upper is not None:
            cls.ID_UPPER_LIMIT["manufacturerpart"] = upper

        logger.debug("fetching attachments from cache...")
        attachments = entity_cache.get('attachment', [])
        upper = max((att['pk'] for att in attachments), default=None)
        if upper is not None:
            cls.ID_UPPER_LIMIT["attachment"] = upper

        logger.debug("fetching supplier parts from cache...")
        supplierparts = entity_cache.get('supplierpart', [])
        upper = max((sup['pk'] for sup in supplierparts), default=None)
        if upper is not None:
            cls.ID_UPPER_LIMIT["supplierpart"] = upper

        logger.info(f"Fetched ID upper limits: {cls.ID_UPPER_LIMIT}")

    @classmethod
    def get_next_id(cls, key):
        cls.ID_UPPER_LIMIT[key] += 1
        return cls.ID_UPPER_LIMIT[key]

    @classmethod
    def list_parts(cls):
        return [{"pk": row["id"], "name": row["name"]} for row in cls.DB_PART_ROWS]
    
    @classmethod
    def write_df_to_csv(cls, df, columns, filename):
        try:
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
        except Exception as e:
            logger.error(f"Error writing DataFrame to CSV {output_path}: {e}")

    @classmethod
    def write_all_db_csv(cls):
        cls.write_df_to_csv(pd.DataFrame(cls.DB_PART_ROWS), cls.DB_PART_COLUMNS, "part_part.csv")
        cls.write_df_to_csv(pd.DataFrame(cls.DB_PARTPARAMETER_ROWS), cls.DB_PARTPARAMETER_COLUMNS, "part_partparameter.csv")
        cls.write_df_to_csv(pd.DataFrame(cls.DB_PARTRELATED_ROWS), cls.DB_PARTRELATED_COLUMNS, "part_partrelated.csv")
        cls.write_df_to_csv(pd.DataFrame(cls.DB_MANUFACTURERPART_ROWS), cls.DB_MANUFACTURERPART_COLUMNS, "company_manufacturerpart.csv")
        cls.write_df_to_csv(pd.DataFrame(cls.DB_ATTACHMENT_ROWS), cls.DB_ATTACHMENT_COLUMNS, "inventree_attachment.csv")
        cls.write_df_to_csv(pd.DataFrame(cls.DB_SUPPLIERPART_ROWS), cls.DB_SUPPLIERPART_COLUMNS, "part_supplierpart.csv")

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
        designator = data.get('designator', '')
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
            "base_cost": "0",
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
    def add_partparameter_db(cls, data):
        id = cls.get_next_id("partparameter")
        out_row = {
            "id": id,
            "data": data.get("data", ""),
            "part_id": data.get("part", ""),
            "template_id": data.get("template", ""),
            "data_numeric": data.get("data_numeric", ""),
            "metadata": "{}"
        }
        cls.DB_PARTPARAMETER_ROWS.append(out_row)
        return id

    @classmethod
    def add_partrelated_db(cls, data):
        id = cls.get_next_id("partrelated")
        out_row = {
            "id": id,
            "part_1_id": data.get("part_1", ""),
            "part_2_id": data.get("part_2", ""),
            "metadata": "{}",
            "note": data.get("note", "")
        }
        cls.DB_PARTRELATED_ROWS.append(out_row)
        return id

    @classmethod
    def add_manufacturerpart_db(cls, data):
        id = cls.get_next_id("manufacturerpart")
        out_row = {
            "id": id,
            "MPN": data.get("MPN", ""),
            "link": "",
            "description": data.get("description", ""),
            "manufacturer_id": data.get("manufacturer", ""),
            "part_id": data.get("part", ""),
            "metadata": "{}",
            "barcode_data": "",
            "barcode_hash": "",
            "notes": data.get("notes", "")
        }

        cls.DB_MANUFACTURERPART_ROWS.append(out_row)
        return id

    @classmethod
    def add_supplierpart_db(cls, data):
        id = cls.get_next_id("supplierpart")
        out_row = {
            "id": id,
            "SKU": data.get("SKU", ""),
            "link": "",
            "description": "",
            "note": "",
            "base_cost": "0",
            "packaging": "",
            "multiple": "0",
            "part_id": data.get("part", ""),
            "supplier_id": data.get("supplier", ""),
            "manufacturer_part_id": "",
            "availability_updated": "",
            "available": "1",
            "barcode_data": "",
            "barcode_hash": "",
            "updated": "",
            "metadata": "{}",
            "pack_quantity": "",
            "pack_quantity_native": "",
            "active": "true",
            "notes": ""
        }
        cls.DB_SUPPLIERPART_ROWS.append(out_row)
        return id
    
    @classmethod
    def add_attachment_db(cls, data):
        id = cls.get_next_id("attachment")
        out_row = {
            "id": id,
            "model_id": data.get("model_id", ""),
            "attachment": data.get("attachment", ""),
            "link": data.get("link", ""),
            "comment": data.get("comment", ""),
            "upload_date": data.get("upload_date", "2025-09-04"),
            "file_size": data.get("file_size", "0"),
            "model_type": data.get("model_type", ""),
            "upload_user_id": "1",
            "metadata": "{}"
        }
        cls.DB_ATTACHMENT_ROWS.append(out_row)
        return id

    @classmethod
    def create(cls, api, entity_type, data) -> tuple:
        """
        Create a CSV row for the given entity_type and data, return an object with .pk attribute.
        Ensures ID counters are fetched once before first use.
        """
        if not cls._id_counters_fetched:
            cls.fetch_id_counters(api)
            cls._id_counters_fetched = True

        if entity_type.__name__ == "Part":
            pk = cls.add_part_row_db(data)
            return pk, ErrorCodes.SUCCESS
        elif entity_type.__name__ == "Parameter":
            pk = cls.add_partparameter_db(data)
            return pk, ErrorCodes.SUCCESS
        elif entity_type.__name__ == "PartRelated":
            pk = cls.add_partrelated_db(data)
            return pk, ErrorCodes.SUCCESS
        elif entity_type.__name__ == "ManufacturerPart":
            pk = cls.add_manufacturerpart_db(data)
            return pk, ErrorCodes.SUCCESS
        elif entity_type.__name__ == "Attachment":
            pk = cls.add_attachment_db(data)
            return pk, ErrorCodes.SUCCESS
        elif entity_type.__name__ == "SupplierPart":
            pk = cls.add_supplierpart_db(data)
            return pk, ErrorCodes.SUCCESS
        else:
            logger.warning(f"CsvDbWriter.create: Unsupported entity type {entity_type.__name__}")
            return None, ErrorCodes.ENTITY_CREATION_FAILED
        
# Create a singleton instance of CsvDbWriter for use in other utils
csv_db_writer = CsvDbWriter