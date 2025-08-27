#!/usr/bin/env python3
"""
Main script for InvenTree operations.
Example usage of the centralized configuration and KiCad plugin class.
"""

import sys
import os
import argparse
import logging
from utils.config import Config
from utils.plugin import KiCadPlugin
from utils.csv_processing import process_database_file, process_configuration_file
from scripts.utils.delete import delete_all, delete_entity_type, list_entity_types
from utils.logging_utils import set_log_level
from inventree.api import InvenTreeAPI

logger = logging.getLogger('InvenTreeCLI')

def main():
    parser = argparse.ArgumentParser(description="InvenTree Management CLI")
    parser.add_argument('--directory', help='Directory containing CSV files to process, relative to main.py')
    parser.add_argument('--delete-all', action='store_true', help='Delete all parts and entities')
    parser.add_argument('--delete-entity', help='Delete all instances of a specific entity type (e.g., Parameter, Part)')
    parser.add_argument('--list-entities', action='store_true', help='List all available entity types that can be deleted')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--verbose', action='store_true', help='Print configuration details')
    
    args = parser.parse_args()
    
    # Set log level
    set_log_level(args.log_level)
    
    # Handle list entities command (no API needed)
    if args.list_entities:
        entity_types = list_entity_types()
        print("Available entity types for deletion:")
        for entity_type in sorted(entity_types):
            print(f"  - {entity_type}")
        return
    
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
    
    if args.delete_all:
        delete_all(api)
        return
    
    if args.delete_entity:
        success = delete_entity_type(api, args.delete_entity)
        if not success:
            sys.exit(1)
        return
    
    # Install and configure the KiCad plugin
    plugin = KiCadPlugin(api)
    plugin.install()
    plugin.configure_global_settings()
    
    # Process CSV files if directory is provided
    if args.directory:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_source_dir = os.path.join(script_dir, args.directory)
        
        # Check if the directory exists
        if not os.path.exists(csv_source_dir):
            logger.error(f"Error: The directory '{csv_source_dir}' does not exist.")
            return
        
        # Process Configuration CSV files first
        for filename in os.listdir(csv_source_dir):
            if filename.endswith('Configuration.csv'):
                process_configuration_file(api, os.path.join(csv_source_dir, filename))
        
        # Then process all other CSV files
        for filename in os.listdir(csv_source_dir):
            if filename.endswith('.csv') and not filename.endswith('Configuration.csv'):
                process_database_file(api, os.path.join(csv_source_dir, filename))
    
        # Update plugin settings at the end
        plugin.update_settings()

if __name__ == "__main__":
    main()