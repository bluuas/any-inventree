"""
Plugin configuration, installation, and update utilities for InvenTree plugins.
"""
import logging
from inventree.api import InvenTreeAPI
from inventree.part import ParameterTemplate
from inventree.plugin import InvenTreePlugin
from .entity_resolver import resolve_entity
import requests

logger = logging.getLogger('kicad-plugin')
logger.setLevel(logging.DEBUG)

INVENTREE_GLOBAL_SETTINGS = {
    "ENABLE_PLUGINS_URL": True,
    "ENABLE_PLUGINS_APP": True,
    "PART_PARAMETER_ENFORCE_UNITS": False
}

KICAD_PLUGIN_PK = "kicad-library-plugin"
INVENTREE_SITE_URL = "http://inventree.localhost" #todo: get from environment variable


kicad_category_cache = {}
def fetch_kicad_categories(api: InvenTreeAPI):
    """Fetch and cache KiCad categories from the plugin."""
    global kicad_category_cache
    try:
        response = requests.get(f"{INVENTREE_SITE_URL}/plugin/{KICAD_PLUGIN_PK}/api/category/", headers={"Authorization": f"Token {api.token}"})
        if response.status_code == 200:
            logger.debug(f"Fetched KiCad categories successfully. Found following categories: {response.json()}")
            kicad_category_cache = {cat['category']['id']: cat for cat in response.json() if 'category' in cat and 'id' in cat['category']}
        else:
            logger.error(f"Failed to fetch KiCad categories: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error fetching KiCad categories: {e}")

def add_category(api: InvenTreeAPI, category_pk: int):
    """
    Add a category to the KiCad plugin if not already present.
    Fetches the cache from the API if the cache is empty.
    """
    global kicad_category_cache
    # Fetch cache if empty
    if not kicad_category_cache:
        fetch_kicad_categories(api)
    if category_pk in kicad_category_cache:
        return
    try:
        HEADERS = {
            "Authorization": f"Token {api.token}",
            "Content-Type": "application/json"
        }
        response = requests.post(f"{INVENTREE_SITE_URL}/plugin/{KICAD_PLUGIN_PK}/api/category/", headers=HEADERS, json={'category': category_pk})
        if response.status_code == 200:
            kicad_category_cache[category_pk] = True
            logger.debug(f"Added category {category_pk} to cache and KiCAD plugin: {response.json()}")
        else:
            logger.error(f"Failed to add category {category_pk} to KiCAD plugin: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error adding generic part category to KiCAD plugin: {e}")

def configure(api: InvenTreeAPI):
    """Configure global settings for InvenTree."""
    try:
        for setting, value in INVENTREE_GLOBAL_SETTINGS.items():
            response_data = api.patch(url=f"settings/global/{setting}/", data={'value': value})
            if response_data is None:
                logger.error(f"Failed to set global setting {setting}.")
                return
            logger.info(f"Set global setting {setting} to {value}.")
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
