from inventree.api import InvenTreeAPI
import os
from dotenv import load_dotenv
import utils.utils as utils
import utils.kicad_plugin as kicad_plugin
import argparse
import logging
from logger import setup_logging  # Import the setup_logging function

def main():
    parser = argparse.ArgumentParser(description="InvenTree CLI")
    parser.add_argument('--delete-all', action='store_true', help='Delete all entities')
    parser.add_argument('-d', '--directory', default='csv-database', help='Directory containing CSV files to process')
    parser.add_argument('--log-level', default='INFO', help='Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')

    load_dotenv()

    API_URL = os.getenv("INVENTREE_API_URL")
    API_USERNAME = os.getenv("INVENTREE_USERNAME")
    API_PASSWORD = os.getenv("INVENTREE_PASSWORD")

    # Parse the arguments first
    args = parser.parse_args()

    # Set up the logger with the specified log level
    setup_logging(getattr(logging, args.log_level.upper(), logging.INFO))

    api = InvenTreeAPI(API_URL, username=API_USERNAME, password=API_PASSWORD)

    logger = logging.getLogger(__name__)  # Define logger for this module

    if args.delete_all:
        utils.delete_all(api)
        return

    # Install the kicad_plugin Plugin for InvenTree
    kicad_plugin.configure(api)
    kicad_plugin.install(api)

    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_source_dir = os.path.join(script_dir, args.directory)

    # Check if the directory exists
    if not os.path.exists(csv_source_dir):
        logger.error(f"Error: The directory '{csv_source_dir}' does not exist.")
        return

    # Process CSV files in the specified directory
    for filename in os.listdir(csv_source_dir):
        if filename.endswith('.csv'):
            utils.process_csv_file(api, os.path.join(csv_source_dir, filename))

    kicad_plugin.update(api)

if __name__ == "__main__":
    main()
