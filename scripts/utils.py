import os
import pandas as pd
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part
import coloredlogs, logging

# Create a logger object.
logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)

def handle_part_category(api, _, data):
    """Handle category entity."""
    name = data['name']

    entity_dict = {category.name: category.pk for category in PartCategory.list(api)}
    if name in entity_dict:
        logger.debug(f"PartCategory '{name}' already exists as ID: {entity_dict[name]}")
        return entity_dict[name]
    
    new_entity = PartCategory.create(api, data)
    logger.info(f"PartCategory '{name}' created successfully!")
    return new_entity.pk

def handle_company(api, _, data):
    """Handle company entity."""
    name = data['name']
    
    entity_dict = {company.name: company.pk for company in Company.list(api)}
    if name in entity_dict:
        logger.debug(f"Supplier '{name}' already exists!")
        return entity_dict[name]
    
    new_entity = Company.create(api, data)
    logger.info(f"Supplier '{name}' created successfully!")
    return new_entity.pk

def handle_part(api, _, data):
    """Handle part entity."""
    name = data['name']
    category_pk = data['category']
    
    entity_dict = {part.name: part.pk for part in Part.list(api)}
    if name in entity_dict:
        logger.debug(f"Part '{name}' already exists!")
        return entity_dict[name]
    
    new_entity = Part.create(api, data)
    logger.info(f"Part '{name}' created successfully in category '{category_pk}'!")
    return new_entity.pk

# Mapping entity types to their handling functions
handler_map = {
    Company: handle_company,
    PartCategory: handle_part_category,
    Part: handle_part,
}

def resolve_entity(api, entity_type, data):
    """Find or create an entity in the InvenTree API."""
    try:
        handler = handler_map.get(entity_type)
        if handler:
            return handler(api, None, data)  # Pass None for the second argument
        else:
            logger.error(f"No handler found for entity type: {entity_type}")
            raise ValueError(f"Invalid entity type: {entity_type}")
    except Exception as e:
        logger.error(f"Error finding or creating {entity_type}: {e}")
        raise

def process_csv_files(api, directory):
    """Process all CSV files in the specified directory."""
    for file in os.listdir(directory):
        if file.endswith('.csv'):
            logger.info(f"Processing '{file}'...")
            try:
                df = pd.read_csv(os.path.join(directory, file))
                df = df.iloc[1:]  # Drop the 2nd row, since it only contains the units

                # Extract suppliers and manufacturers from the relevant columns
                supplier_columns = ['SUPPLIER1', 'SUPPLIER2', 'SUPPLIER3']
                manufacturer_columns = ['MANUFACTURER1', 'MANUFACTURER2', 'MANUFACTURER3']

                # Concatenate all supplier and manufacturer columns into a single Series, convert to string, and drop empty values
                suppliers = pd.concat([df[col].dropna().astype(str).str.strip() for col in supplier_columns], ignore_index=True)
                manufacturers = pd.concat([df[col].dropna().astype(str).str.strip() for col in manufacturer_columns], ignore_index=True)

                # Resolve suppliers and manufacturers
                # for supplier in suppliers.unique():
                #     resolve_entity(api, Company, {'name': supplier, 'is_supplier': True, 'is_manufacturer': False})
                # for manufacturer in manufacturers.unique():
                #     resolve_entity(api, Company, {'name': manufacturer, 'is_supplier': False, 'is_manufacturer': True})

                # Process each row in the CSV file
                for _, row in df.iterrows():
                    category_name = row['CATEGORY']
                    category_pk = 0
                    if category_name:
                        category_pk = resolve_entity(api, PartCategory, {'name': category_name})

                        subcategory_name = row['SUBCATEGORY']
                        if subcategory_name:
                            subcategory_pk = resolve_entity(api, PartCategory, {'name': subcategory_name, 'parent': category_pk})

                    # Prepare part data
                    part_data = {
                        'category': subcategory_pk if subcategory_pk else category_pk,
                        'name': row['NAME'],  # Replace with the actual column name for part
                        'description': row['DESCRIPTION']
                    }
                    # Resolve part
                    part_pk = resolve_entity(api, Part, part_data)

                    supplier1_pk = resolve_entity(api, Company, {'name': row['SUPPLIER1'], 'is_supplier': True, 'is_manufacturer': False})
                    SupplierPart.create(api, {'part': part_pk,'supplier': supplier1_pk, 'SKU': row['SPN1']})
                    supplier2_pk = resolve_entity(api, Company, {'name': row['SUPPLIER2'], 'is_supplier': True, 'is_manufacturer': False})
                    SupplierPart.create(api, {'part': part_pk,'supplier': supplier2_pk, 'SKU': row['SPN2']})
                    supplier3_pk = resolve_entity(api, Company, {'name': row['SUPPLIER3'], 'is_supplier': True, 'is_manufacturer': False})
                    SupplierPart.create(api, {'part': part_pk,'supplier': supplier3_pk, 'SKU': row['SPN3']})

            except Exception as e:
                logger.error(f"Error processing '{file}': {e}")