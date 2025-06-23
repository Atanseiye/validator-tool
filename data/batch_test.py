import streamlit as st
import subprocess
import json
import os
import pandas as pd

# Path to your JSON file
JSON_FILE = "batch.json"

# Initialize the JSON file if it doesn't exist
if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, "w") as f:
        json.dump({"batch_number": 0}, f)

# Function to read batch number
def read_batch_number():
    with open(JSON_FILE, "r") as f:
        data = json.load(f)
    return data["batch_number"]

# Function to write batch number
def write_batch_number(number):
    with open(JSON_FILE, "w") as f:
        json.dump({"batch_number": number}, f)

# Load the current batch number
batch_number = read_batch_number()

# UI
st.title("Batch Number Incrementer")
st.write(f"### Current Batch Number: {batch_number}")

# Button to increment
if st.button("Next"):
    batch_number += 1
    write_batch_number(batch_number)
    st.write('Running process.py with batch number:', batch_number)

    try:
        subprocess.run(
            ["python", "process.py", "--batch_number", str(batch_number)],
            check=True
        )
        st.success(f"Batch number updated to {batch_number}")
        st.rerun()  # Refresh to reflect change


    except subprocess.CalledProcessError as e:
        batch_number -= 1
        write_batch_number(batch_number)
        st.error(f"Failed to fetch data for batch {batch_number + 1}. Batch number reverted to {batch_number}. \n Kindly try again.")
        # st.error(f"Error: {e}")
