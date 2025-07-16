import os
import csv
from inventree.company import Company
from inventree.part import PartCategory, Part

def find_or_create_category(api, category_name, parent_id=None):
    """Find or create a category in the InvenTree API.

    Args:
        api: The API client instance.
        category_name (str): The name of the category to find or create.
        parent_id (int, optional): The ID of the parent category. Defaults to None.

    Returns:
        int: The primary key of the found or newly created category.

    Raises:
        Exception: If there is an error during API calls.
    """
    try:
        # Create a dictionary for fast lookup of categories by name
        category_dict = {category.name: category.pk for category in PartCategory.list(api)}

        # Check if the category already exists
        if category_name in category_dict:
            return category_dict[category_name]
        else:
            # Create a new category if it doesn't exist
            new_category = PartCategory.create(api, {'name': category_name, 'parent': parent_id})
            return new_category.pk
        
    except Exception as e:
        # Handle exceptions (logging, re-raising, etc.)
        print(f"Error finding or creating category: {e}")
        raise

def find_or_create_supplier(api, supplier_name):
    """Find or create a supplier in the InvenTree API.

    Args:
        api: The API client instance.
        supplier_name (str): The name of the supplier to find or create.
    """
    try:
        # Create a dictionary for fast lookup of suppliers by name
        supplier_dict = {supplier.name: supplier.pk for supplier in Company.list(api, is_supplier=True)}

        # Check if the supplier already exists
        if supplier_name in supplier_dict:
            return supplier_dict[supplier_name]
        else:
            # Create a new supplier if it doesn't exist
            new_supplier = Company.create(api, {'name': supplier_name, 'is_supplier': True, 'is_manufacturer': False})
            return new_supplier.pk
    except Exception as e:
        # Handle exceptions (logging, re-raising, etc.)
        print(f"Error finding or creating supplier: {e}")
        raise

def find_or_create_manufacturer(api, manufacturer_name):
    """Find or create a manufacturer in the InvenTree API.

    Args:
        api: The API client instance.
        manufacturer_name (str): The name of the manufacturer to find or create.
    """
    try:
        # Create a dictionary for fast lookup of manufacturers by name
        manufacturer_dict = {manufacturer.name: manufacturer.pk for manufacturer in Company.list(api, is_manufacturer=True)}
        # Check if the manufacturer already exists
        if manufacturer_name in manufacturer_dict:
            return manufacturer_dict[manufacturer_name]
        else:
            # Create a new manufacturer if it doesn't exist
            new_manufacturer = Company.create(api, {'name': manufacturer_name, 'is_manufacturer': True, 'is_supplier': False})
            return new_manufacturer.pk
    except Exception as e:
        # Handle exceptions (logging, re-raising, etc.)
        print(f"Error finding or creating manufacturer: {e}")
        raise

def part_resolve_category(api, category_name, subcategory_name=None):
    """Resolve the category (/or subcategory) name into a category ID."""
    try:
        category_id = find_or_create_category(api, category_name)
        if subcategory_name:
            subcategory_id = find_or_create_category(api, subcategory_name, category_id)
            return subcategory_id
        return category_id
    except Exception as e:
        print(f"Error resolving category: {e}")
        raise
def part_resolve_supplier(api, supplier_name):
    """Resolve the supplier name into a supplier ID."""
    try:
        supplier_id = find_or_create_supplier(api, supplier_name)
        return supplier_id
    except Exception as e:
        print(f"Error resolving supplier: {e}")
        raise
def part_resolve_manufacturer(api, manufacturer_name):
    """Resolve the manufacturer name into a manufacturer ID."""
    try:
        manufacturer_id = find_or_create_manufacturer(api, manufacturer_name)
        return manufacturer_id
    except Exception as e:
        print(f"Error resolving manufacturer: {e}")
        raise

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

                    part_data = {
                        'category': part_resolve_category(api, row['CATEGORY'], row['SUBCATEGORY']),
                        'name': row['NAME'],
                        'description': row['DESCRIPTION'],
                        "initial_supplier": {
                            "supplier": part_resolve_supplier(api, row['SUPPLIER1']),
                            "sku": row['SPN1'],
                            "manufacturer": part_resolve_manufacturer(api, row['MANUFACTURER1']),
                            "mpn": row['MPN1']
                        },
                    }
                    
                    try:
                        part = Part.create(api, part_data)
                        print(f"Created part: {part.name} in category: {part.category}")
                    except Exception as e:
                        print(f"Failed to create part: {e}")
