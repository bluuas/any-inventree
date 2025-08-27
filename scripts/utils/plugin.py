"""
Plugin configuration, installation, and update utilities for InvenTree plugins.
"""
import logging
from inventree.api import InvenTreeAPI
from inventree.part import ParameterTemplate
from inventree.plugin import InvenTreePlugin
from .entity_resolver import resolve_entity
from .config import Config
import requests

logger = logging.getLogger('InvenTreeCLI')
logger.setLevel(logging.DEBUG)

INVENTREE_GLOBAL_SETTINGS = {
    "ENABLE_PLUGINS_URL": True,
    "ENABLE_PLUGINS_APP": True,
    "PART_PARAMETER_ENFORCE_UNITS": False
}

class KiCadPlugin:
    """KiCad plugin management class for InvenTree."""
    
    def __init__(self, api: InvenTreeAPI, plugin_pk: str = None):
        """
        Initialize KiCad plugin manager.
        
        Args:
            api: InvenTree API instance
            plugin_pk: Plugin primary key, defaults to config value
        """
        self.api = api
        self.plugin_pk = plugin_pk or Config.KICAD_PLUGIN_PK
        self.site_url = Config.get_site_url()
        self.category_cache = {}
        
    def fetch_categories(self):
        """Fetch and cache KiCad categories from the plugin."""
        try:
            response = requests.get(
                f"{self.site_url}/plugin/{self.plugin_pk}/api/category/", 
                headers={"Authorization": f"Token {self.api.token}"}
            )
            if response.status_code == 200:
                logger.debug(f"Fetched KiCad categories successfully. Found following categories: {response.json()}")
                self.category_cache = {
                    cat['category']['id']: cat 
                    for cat in response.json() 
                    if 'category' in cat and 'id' in cat['category']
                }
            else:
                logger.error(f"Failed to fetch KiCad categories: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error fetching KiCad categories: {e}")

    def add_category(self, category_pk: int):
        """
        Add a category to the KiCad plugin if not already present.
        Fetches the cache from the API if the cache is empty.
        """
        # Fetch cache if empty
        if not self.category_cache:
            self.fetch_categories()
        if category_pk in self.category_cache:
            return
        try:
            headers = {
                "Authorization": f"Token {self.api.token}",
                "Content-Type": "application/json"
            }
            response = requests.post(
                f"{self.site_url}/plugin/{self.plugin_pk}/api/category/", 
                headers=headers, 
                json={'category': category_pk}
            )
            if response.status_code == 200:
                self.category_cache[category_pk] = True
                logger.debug(f"Added category {category_pk} to cache and KiCAD plugin: {response.json()}")
            else:
                logger.error(f"Failed to add category {category_pk} to KiCAD plugin: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error adding generic part category to KiCAD plugin: {e}")

    def configure_global_settings(self):
        """Configure global settings for InvenTree."""
        try:
            for setting, value in INVENTREE_GLOBAL_SETTINGS.items():
                response_data = self.api.patch(url=f"settings/global/{setting}/", data={'value': value})
                if response_data is None:
                    logger.error(f"Failed to set global setting {setting}.")
                    return
                logger.info(f"Set global setting {setting} to {value}.")
        except Exception as e:
            logger.error(f"Error configuring global settings: {e}")

    def install(self):
        """Install and activate the KiCad plugin."""
        try:
            plugins = InvenTreePlugin.list(self.api)
            for plugin in plugins:
                logger.debug(f"Plugin: pk: {plugin.pk}, name: {plugin.name}")
            kicad_plugin = next((plugin for plugin in plugins if plugin.pk == self.plugin_pk), None)
            if kicad_plugin:
                logger.info("KiCad plugin is already installed. Trying to activate.")
            else:
                response_data = self.api.post(url="plugins/install/", data={
                    # 'url': 'git+https://github.com/bluuas/inventree_kicad',
                    'url': 'git+https://github.com/afkiwers/inventree_kicad',
                    'packagename': 'inventree-kicad-plugin',
                    'confirm': True,
                })
                if response_data is None:
                    logger.error("Failed to install InvenTree plugin.")
                    return
                logger.info(f"Installed InvenTree plugin: {response_data}")
            response_data = self.api.patch(url=f"plugins/{self.plugin_pk}/activate/", data={'active': True})
            if response_data is None:
                logger.error("Failed to activate KiCad plugin.")
                return
            logger.info("KiCad plugin is active.")
        except Exception as e:
            logger.error(f"Error installing or activating KiCad plugin: {e}")
            raise

    def update_settings(self):
        """Update settings for the KiCad plugin."""
        footprint_pk = resolve_entity(self.api, ParameterTemplate, {'name': 'FOOTPRINT'})
        symbol_pk = resolve_entity(self.api, ParameterTemplate, {'name': 'SYMBOL'})
        designator_pk = resolve_entity(self.api, ParameterTemplate, {'name': 'DESIGNATOR'})
        value_pk = resolve_entity(self.api, ParameterTemplate, {'name': 'VALUE'})
        visibility_pk = resolve_entity(self.api, ParameterTemplate, {'name': 'KICAD_VISIBILITY'})
        
        settings = {
            'KICAD_FOOTPRINT_PARAMETER': footprint_pk,
            'KICAD_SYMBOL_PARAMETER': symbol_pk,
            'KICAD_REFERENCE_PARAMETER': designator_pk,
            'KICAD_VALUE_PARAMETER': value_pk,
            'KICAD_FIELD_VISIBILITY_PARAMETER': visibility_pk,
        }
        try:
            for key, value in settings.items():
                self.api.patch(url=f"plugins/{self.plugin_pk}/settings/{key}/", data={'value': value})
                logger.debug(f"Updated KiCad setting {key} to {value}.")
        except Exception as e:
            logger.error(f"Error updating KiCad plugin settings: {e}")