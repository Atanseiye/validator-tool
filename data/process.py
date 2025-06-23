import re
import os
import sys
import pandas as pd
import argparse
from pathlib import Path

from config import config 
from db import fetch_data, push_data

import pandas as pd
import glob
import argparse


# Parse arguments from the terminal
parser = argparse.ArgumentParser(description="Fetch a batch of data from MongoDB.")
parser.add_argument("--batch_number", type=int, required=True, help="The batch number to fetch.")
parser.add_argument("--username", type=str, required=True, help="Username for the task.")

args = parser.parse_args()

# Define database configuration
collection = config['yoruba_collection']
batch_size = 1000
batch_number = args.batch_number
username = args.username

# Push the data to the database collection
data = fetch_data(collection, batch_size=batch_size, batch_number=batch_number)

# Remove all .csv files in the current directory
for file in glob.glob("*.csv"):
    try:
        if file:
            os.remove(file)
            print(f"Deleted: {file}")
        else:
            print(f"No existing csv file in this directory.")
    except Exception as e:
        print(f"Failed to delete {file}: {e}")

data.to_csv(f'fetched_data/{username}/batch_{batch_number}.csv', index=False, encoding='utf-8-sig')
print(f'Wrote data to batch_{batch_number}.csv')