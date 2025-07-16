import os
import csv
from inventree.part import PartCategory, Part

def find_or_create_category(api, category_name, parent_id=None):
    """Find or create a category in the InvenTree API."""
    category_list = PartCategory.list(api)
    for category in category_list:
        if category.name == category_name:
            return category.pk
    
    new_category = PartCategory.create(api, {'name': category_name, 'parent': parent_id})
    return new_category.pk

def process_csv_files(api, directory):
    """Process all CSV files in the specified directory."""
    for file in os.listdir(directory):
        if file.endswith('.csv'):
            print(f"Processing {file}...")
            with open(os.path.join(directory, file), 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Skip header and 2nd row
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
