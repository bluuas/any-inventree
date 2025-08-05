from inventree.api import InvenTreeAPI
from inventree.part import ParameterTemplate
from inventree.plugin import InvenTreePlugin
from .utils import resolve_entity
# import requests
# from dotenv import load_dotenv
# import os

import logging
import coloredlogs
logger = logging.getLogger(__name__)
coloredlogs.install(logging.INFO, logger=logger)

# load_dotenv()
# load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# INVENTREE_SITE_URL = os.getenv("INVENTREE_SITE_URL", "http://inventree.localhost")

INVENTREE_GLOBAL_SETTINGS = {
    "ENABLE_PLUGINS_URL",
    "ENABLE_PLUGINS_APP"
}

KICAD_PLUGIN_PK = "kicad-library-plugin"  # Ensure this constant is defined

# kicad_category_dict = {}

# def get_headers(api):
#     return {
#         "Authorization": f"Token {api.token}",
#         "Content-Type": "application/json"
#     }

# def get_active_categories(api):
#     response = requests.get(f"{INVENTREE_SITE_URL}/plugin/{KICAD_PLUGIN_PK}/api/category/", headers=get_headers(api))
#     if response.status_code == 200:
#         return response.json()  # Return the list of active categories
#     else:
#         logger.error(f"Failed to retrieve active categories: {response.status_code} - {response.text}")
#         return []

# def add_category(api, pk):
#     if pk in kicad_category_dict:  # Check if already cached
#         logger.debug(f"Category {pk} is already in the cache.")
#         return

#     active_categories = get_active_categories(api)
    
#     if any(category['category']['id'] == pk for category in active_categories):  # Check if exists
#         logger.debug(f"Category {pk} already exists.")
#         kicad_category_dict[pk] = True  # Cache it
#         return
#     # create new
#     try:
#         response = requests.post(f"{INVENTREE_SITE_URL}/plugin/{KICAD_PLUGIN_PK}/api/category/", headers=get_headers(api), json={'category': pk})
#         if response.status_code == 201:  # Success
#             kicad_category_dict[pk] = True  # Cache it
#             logger.debug(f"Added category {pk}: {response.json()}")
#         else:
#             logger.error(f"Failed to add category {pk}: {response.status_code} - {response.text}")
#     except Exception as e:
#         logger.error(f"Error adding category {pk}: {e}")

def configure(api: InvenTreeAPI):
    """Configure global settings for InvenTree."""
    try:
        for setting in INVENTREE_GLOBAL_SETTINGS:
            response_data = api.patch(url=f"settings/global/{setting}/", data={'value': True})
            if response_data is None:
                logger.error(f"Failed to set global setting {setting}.")
                return
            logger.info(f"Set global setting {setting} to True.")
    except Exception as e:
        logger.error(f"Error configuring global settings: {e}")

def install(api: InvenTreeAPI):
    """Install and activate the KiCad plugin."""
    try:
        plugins = InvenTreePlugin.list(api)
        for plugin in plugins:
            logger.debug(f"Plugin: pk: {plugin.pk}, name: {plugin.name}")

        kicad_plugin = next((plugin for plugin in plugins if plugin.pk == KICAD_PLUGIN_PK), None)
        
        if kicad_plugin:
            logger.info("KiCad plugin is already installed. Trying to activate.")
        else:
            response_data = api.post(url="plugins/install/", data={
                'url': 'git+https://github.com/bluuas/inventree_kicad',
                'packagename': 'inventree-kicad-plugin',
                'confirm': True,
            })
            if response_data is None:
                logger.error("Failed to install InvenTree plugin.")
                return
            logger.info(f"Installed InvenTree plugin: {response_data}")

        response_data = api.patch(url=f"plugins/{KICAD_PLUGIN_PK}/activate/", data={'active': True})
        if response_data is None:
            logger.error("Failed to activate KiCad plugin.")
            return
        logger.info("KiCad plugin is active.")
    except Exception as e:
        logger.error(f"Error installing or activating KiCad plugin: {e}")
        quit()

def update(api: InvenTreeAPI):
    """Update settings for the KiCad plugin."""
    footprint_pk = resolve_entity(api, ParameterTemplate, {'name': 'FOOTPRINT'})
    symbol_pk = resolve_entity(api, ParameterTemplate, {'name': 'SYMBOL'})
    designator_pk = resolve_entity(api, ParameterTemplate, {'name': 'DESIGNATOR'})
    value_pk = resolve_entity(api, ParameterTemplate, {'name': 'VALUE'})

    settings = {
        'KICAD_FOOTPRINT_PARAMETER': footprint_pk,
        'KICAD_SYMBOL_PARAMETER': symbol_pk,
        'KICAD_REFERENCE_PARAMETER': designator_pk,
        'KICAD_VALUE_PARAMETER': value_pk,
    }
    try:
        for key, value in settings.items():
            api.patch(url=f"plugins/{KICAD_PLUGIN_PK}/settings/{key}/", data={'value': value})
            logger.debug(f"Updated KiCad setting {key} to {value}.")
    except Exception as e:
        logger.error(f"Error updating KiCad plugin settings: {e}")
