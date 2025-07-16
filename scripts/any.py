from inventree.api import InvenTreeAPI
from inventree.part import PartCategory, Part
import os
import csv
from dotenv import load_dotenv
from utils import find_or_create_category, process_csv_files

load_dotenv()

API_URL = "http://inventree.localhost/api/"
API_USERNAME = os.getenv("INVENTREE_USERNAME")
API_PASSWORD = os.getenv("INVENTREE_PASSWORD")

api = InvenTreeAPI(API_URL, username=API_USERNAME, password=API_PASSWORD)

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Process CSV files in the specified directory
process_csv_files(api, os.path.join(script_dir, 'csv-database'))