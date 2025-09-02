#!/usr/bin/env python3
"""
Main script for InvenTree operations.
Example usage of the centralized configuration and KiCad plugin class.
"""

import sys
import argparse
import logging
from utils.config import Config
from utils.plugin import KiCadPlugin
from utils.logging_utils import set_log_level
from utils.units import create_default_units
from inventree.api import InvenTreeAPI

logger = logging.getLogger('InvenTreeCLI')

def main():
    parser = argparse.ArgumentParser(description="InvenTree Management CLI")
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--verbose', action='store_true', help='Print configuration details')
    
    args = parser.parse_args()
    
    # Set log level
    set_log_level(args.log_level)

    # Validate configuration
    missing_vars = Config.validate_required()
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
        
    # Print configuration for debugging
    if args.verbose:
        Config.print_config()
        
    # Initialize API
    credentials = Config.get_api_credentials()
    api = InvenTreeAPI(credentials['url'], username=credentials['username'], password=credentials['password'])
    
    # Install and configure the KiCad plugin
    plugin = KiCadPlugin(api)
    plugin.install()
    plugin.configure_global_settings()
    plugin.update_settings()

    # create physical units
    create_default_units(api)

if __name__ == "__main__":
    main()