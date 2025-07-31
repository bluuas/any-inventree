from inventree.api import InvenTreeAPI
from inventree.part import ParameterTemplate
from inventree.plugin import InvenTreePlugin
from utils.utils import resolve_entity
from logger import setup_logger

logger = setup_logger(__name__)

INVENTREE_GLOBAL_SETTINGS = {
    "ENABLE_PLUGINS_URL",
    "ENABLE_PLUGINS_APP"
}

KICAD_PLUGIN_PK = "kicad-library-plugin"  # Ensure this constant is defined

def configure(api: InvenTreeAPI):
    """Configure global settings for InvenTree."""
    try:
        for setting in INVENTREE_GLOBAL_SETTINGS:
            response_data = api.patch(url=f"/settings/global/{setting}/", data={'value': True})
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
            response_data = api.post(url="/plugins/install/", data={
                'url': 'git+https://github.com/bluuas/inventree_kicad',
                'packagename': 'inventree-kicad-plugin',
                'confirm': True,
            })
            if response_data is None:
                logger.error("Failed to install InvenTree plugin.")
                return
            logger.info(f"Installed InvenTree plugin: {response_data}")

        response_data = api.patch(url=f"/plugins/{KICAD_PLUGIN_PK}/activate/", data={'active': True})
        if response_data is None:
            logger.error("Failed to activate KiCad plugin.")
            return
        logger.info("KiCad plugin is active.")
    except Exception as e:
        logger.error(f"Error installing or activating KiCad plugin: {e}")

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
            api.patch(url=f"/plugins/{KICAD_PLUGIN_PK}/settings/{key}/", data={'value': value})
            logger.debug(f"Updated KiCad setting {key} to {value}.")
    except Exception as e:
        logger.error(f"Error updating KiCad plugin settings: {e}")
