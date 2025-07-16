from inventree.api import InvenTreeAPI
import os
from dotenv import load_dotenv
from utils import process_csv_files

def main():
    load_dotenv()

    API_URL = "http://inventree.localhost/api/"
    API_USERNAME = os.getenv("INVENTREE_USERNAME")
    API_PASSWORD = os.getenv("INVENTREE_PASSWORD")

    api = InvenTreeAPI(API_URL, username=API_USERNAME, password=API_PASSWORD)

    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Process CSV files in the specified directory
    process_csv_files(api, os.path.join(script_dir, 'csv-database'))

if __name__ == "__main__":
    main()
