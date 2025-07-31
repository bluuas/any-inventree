from inventree.api import InvenTreeAPI
import os
from dotenv import load_dotenv
import utils.utils as utils
import utils.kicad_plugin as kicad_plugin
import argparse

def main():
    parser = argparse.ArgumentParser(description="InvenTree CLI")
    parser.add_argument('--delete-all', action='store_true', help='Delete all entities')
    parser.add_argument('-d', '--directory', required=True, help='Directory containing CSV files')

    load_dotenv()

    API_URL = os.getenv("INVENTREE_API_URL")
    API_USERNAME = os.getenv("INVENTREE_USERNAME")
    API_PASSWORD = os.getenv("INVENTREE_PASSWORD")

    api = InvenTreeAPI(API_URL, username=API_USERNAME, password=API_PASSWORD)
    args = parser.parse_args()

    if args.delete_all:
        utils.delete_all(api)
        return

    # Install the kicad_plugin Plugin for InvenTree
    kicad_plugin.configure(api)
    kicad_plugin.install(api)

    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_source_dir = os.path.join(script_dir, args.directory)

    # Process CSV files in the specified directory
    for filename in os.listdir(csv_source_dir):
        if filename.endswith('.csv'):
            utils.process_csv_file(api, os.path.join(csv_source_dir, filename))

    kicad_plugin.update(api)

if __name__ == "__main__":
    main()
