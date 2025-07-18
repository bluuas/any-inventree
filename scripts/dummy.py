from inventree.api import InvenTreeAPI
import os
from dotenv import load_dotenv

import pandas as pd
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part, Parameter, ParameterTemplate, PartCategoryParameterTemplate
import coloredlogs, logging
from tqdm import tqdm

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)

# Caches for entities
cache_part_category = {}
cache_company = {}
cache_part = {}
cache_parameter = {}
cache_parameter_template = {}
cache_part_category_parameter_template = {}

# Mapping of entity types to their caches
cache_mapping = {
    Company: cache_company,
    Parameter: cache_parameter,
    ParameterTemplate: cache_parameter_template,
    Part: cache_part,
    PartCategory: cache_part_category,
    PartCategoryParameterTemplate: cache_part_category_parameter_template,
}

# Lookup Table for identifiers per entity type
identifier_lut = {
    Company: ['name'],
    Parameter: ['part', 'template'],
    ParameterTemplate: ['name'],
    Part: ['name', 'category'],
    PartCategory: ['name'],
    PartCategoryParameterTemplate: ['category', 'parameter_template']
}

def delete_all(api):
    # Step 1: Delete all parts
    parts_dict = Part.list(api)
    logger.info(f"Deleting {len(parts_dict)} parts")
    
    for part in parts_dict:
        try:
            logger.info(f"Deactivating part: {part.name} with PK: {part.pk}")
            part.save(data={
                'active': False,
                'name': f"{part.name}",
                'minimum_stock': 0,
            }, method='PUT')  # Use PUT to update the part
            logger.info(f"Deleting part: {part.name} with PK: {part.pk}")
            part.delete()  # Now delete the part
        except Exception as e:
            logger.error(f"Error processing part '{part.name}': {e}")

    # Step 2: Delete other entities
    for entity_type, cache in cache_mapping.items():
        try:
            entities = entity_type.list(api)
            logger.info(f"Deleting {len(entities)} instances of {entity_type.__name__}")
            for entity in entities:
                entity.delete()
            cache.clear()
        except Exception as e:
            logger.error(f"Error deleting {entity_type.__name__} instances: {e}")

def resolve_entity(api, entity_type, data):
    identifiers = identifier_lut.get(entity_type, [])
    if not identifiers:
        logger.error(f"No identifiers found for entity type: {entity_type.__name__}")
        return None
    
    cache = cache_mapping.get(entity_type, {})
    
    # Create a composite key from the identifiers
    composite_key = tuple(data[identifier] for identifier in identifiers if identifier in data)
    
    # Check cache first
    entity_id = cache.get(composite_key)
    if entity_id is not None:
        logger.debug(f"{entity_type.__name__} '{composite_key}' found in cache with ID: {entity_id}")
        return entity_id

    # Fetch all entities from the API and populate the cache
    entity_dict = {tuple(getattr(entity, identifier) for identifier in identifiers): entity.pk for entity in entity_type.list(api)}
    cache.update(entity_dict)

    # Check again after updating the cache
    entity_id = cache.get(composite_key)
    if entity_id is not None:
        logger.debug(f"{entity_type.__name__} '{composite_key}' already exists in database with ID: {entity_id}")
        return entity_id

    # Create new entity if not found
    try:
        new_entity = entity_type.create(api, data)
        logger.info(f"{entity_type.__name__} '{composite_key}' created successfully at ID: {new_entity.pk}")
        cache[composite_key] = new_entity.pk  # Update cache with new entity
        return new_entity.pk
    except Exception as e:
        logger.error(f"! Error creating {entity_type.__name__} '{composite_key}': {e}")
        return None


def main():
    load_dotenv()

    API_URL = "http://inventree.localhost/api/"
    API_USERNAME = os.getenv("INVENTREE_USERNAME")
    API_PASSWORD = os.getenv("INVENTREE_PASSWORD")

    api = InvenTreeAPI(API_URL, username=API_USERNAME, password=API_PASSWORD)

    try:
        delete_all(api)
        pass
    except Exception as e:
        logger.error(f"Error deleting InvenTree: {e}")
        return

    try:
        category_parameter_template_pk = resolve_entity(api, ParameterTemplate, {
            'name': 'category_parameter',
            'description': 'This is a category parameter template',
            'default': 'default category.parameter'
        })
        subcategory1_parameter_template_pk = resolve_entity(api, ParameterTemplate, {
            'name':'subcategory1_parameter',
            'description': 'This is a subcategory1 parameter template',
            'default': 'default subcategory1.parameter'
        })
        subcategory2_parameter_template_pk = resolve_entity(api, ParameterTemplate, {
            'name':'subcategory2_parameter',
            'description': 'This is a subcategory2 parameter template',
            'default': 'default subcategory2.parameter'
        })
    except Exception as e:
        logger.error(f"Error resolving ParameterTemplate: {e}")
        return
    
    try:
        category_pk = resolve_entity(api, PartCategory, {'name': 'dummy_category'})
        subcategory1_pk = resolve_entity(api, PartCategory, {'name': 'dummy_subcategory1', 'parent': category_pk})
        subcategory2_pk = resolve_entity(api, PartCategory, {'name': 'dummy_subcategory2', 'parent': category_pk})
    except Exception as e:
        logger.error(f"Error creating PartCategory or Subcategory: {e}")

    try:
        # list all the existing parameter template names
        p = [template.name for template in ParameterTemplate.list(api)]
        logger.info(f"Existing parameter template names: {p}")

        part_category_parameter_template_pk = resolve_entity(api, PartCategoryParameterTemplate, {
            'category': category_pk,
            'parameter_template': category_parameter_template_pk,
            'default_value': 'default PartCategoryParameterTemplate'
        })

        part_subcategory1_parameter_template_pk = resolve_entity(api, PartCategoryParameterTemplate, {
            'category': subcategory1_pk,
            'parameter_template': subcategory1_parameter_template_pk,
            'default_value': 'default PartCategoryParameterTemplate'
        })

        part_subcategory2_parameter_template_pk = resolve_entity(api, PartCategoryParameterTemplate, {
            'category': subcategory2_pk,
            'parameter_template': subcategory2_parameter_template_pk,
            'default_value': 'default PartCategoryParameterTemplate'
        })
    except Exception as e:
        logger.error(f"Error resolving PartCategoryParameterTemplate: {e}")

        
    try:
        dummy_part1_pk = resolve_entity(api, Part, {
            'name': 'dummy_part1',
            'category': category_pk,
            'description': 'This is a dummy part description',
            'copy_category_parameters': True,
        })
        dummy_part2_pk = resolve_entity(api, Part, {
            'name': 'dummy_part2',
            'category': subcategory1_pk,
            'description': 'This is a dummy part description',
            'copy_category_parameters': True,
        })
        dummy_part3_pk = resolve_entity(api, Part, {
            'name': 'dummy_part3',
            'category': subcategory2_pk,
            'description': 'This is a dummy part description',
            'copy_category_parameters': True,
        })

    except Exception as e:
        logger.error(f"Error creating Part: {e}")

    # try:
    #     resolve_parameter(api, Parameter, {
    #         'part': dummy_part1_pk,
    #         'template': category_parameter_template_pk,
    #         'data': "some Parameter data"
    #     })
    # except Exception as e:
    #     logger.error(f"Error creating Parameter for Part {e}")


if __name__ == "__main__":
    main()
