from inventree.api import InvenTreeAPI
from inventree.company import SupplierPart, Company, ManufacturerPart
from inventree.part import PartCategory, Part
from inventree.base import InventreeObject
import os
import csv
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://inventree.localhost/api/"
API_USERNAME = os.getenv("INVENTREE_USERNAME")
API_PASSWORD = os.getenv("INVENTREE_PASSWORD")

api = InvenTreeAPI(API_URL, username=API_USERNAME, password=API_PASSWORD)

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

def find_or_create_category(api, category_name, parent_id=None):
    category_list = PartCategory.list(api)
    for category in category_list:
        if category.name == category_name:
            return category.pk
    
    new_category = PartCategory.create(api, {'name': category_name, 'parent': parent_id})
    return new_category.pk

# loop through all csv files from csv-database folder
# header line example for Capacitors:
# CATEGORY	SUBCATEGORY	DESCRIPTION	VALUE	DIELECTRIC	HEIGHT	PACKAGE	SYMBOL	FOOTPRINT	CREATED	MANUFACTURER1	MPN1	DSLINK1	SUPPLIER1	SPN1	STATUS1	MANUFACTURER2	MPN2	DSLINK2	SUPPLIER2	SPN2	STATUS2	MANUFACTURER3	MPN3	DSLINK3	SUPPLIER3	SPN3	STATUS3
for file in os.listdir(os.path.join(script_dir, f'csv-database')):
    if file.endswith('.csv'):
        print(f"Processing {file}...")
        with open(os.path.join(script_dir, f'csv-database/{file}'), 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # skip header and 2nd row
                if reader.line_num <= 2:
                    continue

                category = row['CATEGORY']
                subcategory = row['SUBCATEGORY']
                parent_category_id = find_or_create_category(api, category)
                subcategory_id = None
                if parent_category_id and subcategory:
                    subcategory_id = find_or_create_category(api, subcategory, parent_category_id)
                
                part_data = {
                    'category': subcategory_id if subcategory_id else parent_category_id,
                    'name': row['DESCRIPTION'],
                    # 'value': row['VALUE'],
                    # 'dielectric': row['DIELECTRIC'],
                    # 'height': row['HEIGHT'],
                    # 'package': row['PACKAGE'],
                    'symbol': row['SYMBOL'],
                    'footprint': row['FOOTPRINT'],
                    'created': row['CREATED'],
                    'manufacturer1': row['MANUFACTURER1'],
                    'mpn1': row['MPN1'],
                    'dlink1': row['DSLINK1'],
                    'supplier1': row['SUPPLIER1'],
                    'spn1': row['SPN1'],
                    'status1': row['STATUS1'],
                    'manufacturer2': row['MANUFACTURER2'],
                    'mpn2': row['MPN2'],
                    'dlink2': row['DSLINK2'],
                    'supplier2': row['SUPPLIER2'],
                    'spn2': row['SPN2'],
                    'status2': row['STATUS2'],
                    'manufacturer3': row['MANUFACTURER3'],
                    'mpn3': row['MPN3'],
                    'dlink3': row['DSLINK3'],
                    'supplier3': row['SUPPLIER3'],
                    'spn3': row['SPN3'],
                    'status3': row['STATUS3'],
                }
                try:
                    part = Part.create(api, part_data)
                    print(f"Created part: {part.name} in category: {part.category}")
                except Exception as e:
                    print(f"Failed to create part: {e}")