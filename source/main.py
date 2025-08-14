import logging
import coloredlogs
import os
from dotenv import load_dotenv
import argparse
from inventree.api import InvenTreeAPI

# Import refactored utilities
from utils.logging_utils import logger, set_log_level
from utils.delete_utils import delete_all
from utils.plugin import KiCadPlugin
from utils.csv_processing import process_database_file, process_configuration_file


def main():
    """
    Main entry point for the InvenTree CLI.
    Parses arguments, sets up logging, connects to API, and processes CSV files.
    """
    parser = argparse.ArgumentParser(description="InvenTree CLI")
    parser.add_argument('--delete-all', action='store_true', help='Delete all entities')
    parser.add_argument('-d', '--directory', default='csv-database', help='Directory containing CSV files to process')
    parser.add_argument('--log-level', default='INFO', help='Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')

    load_dotenv()

    API_URL = os.getenv("INVENTREE_API_URL")
    API_USERNAME = os.getenv("INVENTREE_USERNAME")
    API_PASSWORD = os.getenv("INVENTREE_PASSWORD")
    SITE_URL = os.getenv("INVENTREE_SITE_URL", "http://inventree.localhost")

    args = parser.parse_args()
    set_log_level(args.log_level)

    api = InvenTreeAPI(API_URL, username=API_USERNAME, password=API_PASSWORD)

    if args.delete_all:
        delete_all(api)
        return

    # Install and configure the KiCad plugin
    plugin = KiCadPlugin(api)
    plugin.configure_global_settings()
    plugin.install()

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
            pass
            process_database_file(api, os.path.join(csv_source_dir, filename), site_url=SITE_URL)

    plugin.update_settings()

if __name__ == "__main__":
    main()
