import argparse
import json
import os
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

# API endpoint and authentication
API_URL = "http://inventree.localhost/api/"
API_KEY = os.getenv("INVENTREE_API_TOKEN")

HEADERS = {
    "Authorization": f"Token {API_KEY}",
    "Content-Type": "application/json"
}

def add_manufacturer(data_file):
    # Function to add manufacturers
    with open(data_file, 'r') as file:
        manufacturers = json.load(file)
    for manufacturer_data in manufacturers:
        response = requests.post(f"{API_URL}company/", headers=HEADERS, json=manufacturer_data)
        print("Response:", response.json())

def add_supplier(data_file):
    # Function to add suppliers
    with open(data_file, 'r') as file:
        suppliers = json.load(file)
    for supplier_data in suppliers:
        response = requests.post(f"{API_URL}company/", headers=HEADERS, json=supplier_data)
        print("Response:", response.json())

def add_categories(categories, parent_id=None):
    # Dictionary to hold existing category names and their IDs
    existing_categories = {}

    # First, check for existing categories and populate the dictionary
    for category_data in categories:
        category_name = category_data["name"]
        # Check if the category already exists
        response = requests.get(f"{API_URL}part/category/?name={category_name}", headers=HEADERS)
        if response.status_code == 200 and response.json():
            # If it exists, store the pk
            existing_categories[category_name] = response.json()[0]['pk']
            print(f"Category '{category_name}' already exists with ID: {existing_categories[category_name]}")
        else:
            # If it doesn't exist, create it
            response = requests.post(f"{API_URL}part/category/", headers=HEADERS, json={"name": category_name, "parent": parent_id})
            if response.status_code == 201:
                created_category = response.json()
                existing_categories[category_name] = created_category['pk']
                print(f"PartCategory '{category_name}' created successfully under '{parent_id}'!")
            else:
                print(f"Failed to create PartCategory '{category_name}'.")
                print("Status Code:", response.status_code)
                print("Response:", response.json())

        # Now handle subcategories recursively
        if "subcategories" in category_data:
            subcategories = category_data["subcategories"]
            add_categories(subcategories, existing_categories[category_name])

def delete_category(category_id):
    """Delete a category by ID."""
    response = requests.delete(f"{API_URL}part/category/{category_id}/", headers=HEADERS)
    
    if response.status_code == 204:
        print(f"Category with ID '{category_id}' deleted successfully.")
    else:
        print(f"Failed to delete category with ID '{category_id}'.")
        print("Status Code:", response.status_code)
        print("Response:", response.json())

def list_categories():
    """List all categories."""
    response = requests.get(f"{API_URL}part/category/", headers=HEADERS)
    
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to retrieve categories.")
        print("Status Code:", response.status_code)
        return []
    
def delete_all_categories():
    """Delete all categories."""
    categories = list_categories()
    for category in categories:
        delete_category(category['pk'])

def main():
    parser = argparse.ArgumentParser(description="InvenTree CLI")
    subparsers = parser.add_subparsers(dest='command')

    # Add manufacturer command
    parser_add_manufacturer = subparsers.add_parser('add-manufacturer', help='Add manufacturers')
    parser_add_manufacturer.add_argument('data_file', help='Path to the manufacturers JSON file')

    # Add supplier command
    parser_add_supplier = subparsers.add_parser('add-supplier', help='Add suppliers')
    parser_add_supplier.add_argument('data_file', help='Path to the suppliers JSON file')

    # Add category command
    parser_add_category = subparsers.add_parser('add-category', help='Add categories')
    parser_add_category.add_argument('data_file', help='Path to the categories JSON file')

    # Delete category command
    parser_delete_category = subparsers.add_parser('delete-category', help='Delete a category')
    parser_delete_category.add_argument('category_id', type=int, nargs='?', help='ID of the category to delete')
    parser_delete_category.add_argument('-a', '--all', action='store_true', help='Delete all categories')

    args = parser.parse_args()

    if args.command == 'add-manufacturer':
        add_manufacturer(args.data_file)
    elif args.command == 'add-supplier':
        add_supplier(args.data_file)
    elif args.command == 'add-category':
        with open(args.data_file, 'r') as file:
            categories = json.load(file)
            add_categories(categories)
    elif args.command == 'delete-category':
        if args.all:
            delete_all_categories()
        elif args.category_id is not None:
            delete_category(args.category_id)
        else:
            print("Error: You must specify a category ID or use -a to delete all categories.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()