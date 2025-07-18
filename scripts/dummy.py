from inventree.api import InvenTreeAPI
import os
from dotenv import load_dotenv

import pandas as pd
from inventree.company import Company, SupplierPart, ManufacturerPart
from inventree.part import PartCategory, Part, Parameter, ParameterTemplate, PartCategoryParameterTemplate
import coloredlogs, logging
from tqdm import tqdm

from utils import resolve_entity

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

    # ----------------- create the necessary parameter templates ----------------- #
    try:
        category_parameter_template_symbol_pk = resolve_entity(api, ParameterTemplate, {
            'name': 'symbol',
            'description': 'The path to the KiCad symbol',
            'default': 'symbol default path'
        })
        category_parameter_template_footprint_pk = resolve_entity(api, ParameterTemplate, {
            'name': 'footprint',
            'description': 'The path to the KiCad footprint',
            'default': 'footprint default path'
        })
        subcategory_parameter_template_resistance_pk = resolve_entity(api, ParameterTemplate, {
            'name':'resistance',
            'description': 'Resistance in ohms',
            'default': '0'
        })
        subcategory_parameter_template_capacitance_pk = resolve_entity(api, ParameterTemplate, {
            'name':'capacitance',
            'description': 'Capacitance in farads',
            'default': '0'
        })
    except Exception as e:
        logger.error(f"Error resolving ParameterTemplate: {e}")
        return
    
    # ------------------ create the categories and subcategories ----------------- #
    try:
        category_passives_pk = resolve_entity(api, PartCategory, {'name': 'dummy_category'})
        subcategory_resistors_pk = resolve_entity(api, PartCategory, {'name': 'dummy_subcategory1', 'parent': category_passives_pk})
        subcategory_capacitors_pk = resolve_entity(api, PartCategory, {'name': 'dummy_subcategory2', 'parent': category_passives_pk})
    except Exception as e:
        logger.error(f"Error creating PartCategory or Subcategory: {e}")

    try:
        part_category_parameter_template_symbol_pk = resolve_entity(api, PartCategoryParameterTemplate, {
            'category': category_passives_pk,
            'parameter_template': category_parameter_template_symbol_pk,
            'default_value': 'default PartCategoryParameterTemplate path'
        })

        part_subcategory1_parameter_template_pk = resolve_entity(api, PartCategoryParameterTemplate, {
            'category': subcategory_resistors_pk,
            'parameter_template': subcategory_parameter_template_resistance_pk,
            'default_value': 'default PartCategoryParameterTemplate'
        })

        part_subcategory2_parameter_template_pk = resolve_entity(api, PartCategoryParameterTemplate, {
            'category': subcategory_capacitors_pk,
            'parameter_template': subcategory_parameter_template_capacitance_pk,
            'default_value': 'default PartCategoryParameterTemplate'
        })
    except Exception as e:
        logger.error(f"Error resolving PartCategoryParameterTemplate: {e}")

        
    try:
        dummy_part1_pk = resolve_entity(api, Part, {
            'name': 'dummy_part1',
            'category': category_passives_pk,
            'description': 'This is a dummy part description',
            'copy_category_parameters': True,            
        })
        myresistor_pk = resolve_entity(api, Part, {
            'name': 'myResistor1',
            'category': subcategory_resistors_pk,
            'description': 'Resistor 0805 1.2k 10% 10V',
            'copy_category_parameters': True,
        })
        mycapacitor_pk = resolve_entity(api, Part, {
            'name': 'myCapacitor1',
            'category': subcategory_capacitors_pk,
            'description': 'Capacitor 0805 1uF 10% 10V',
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
