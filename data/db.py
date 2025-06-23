from pymongo import MongoClient
from pymongo.errors import OperationFailure
from config import config
import streamlit as st
import pandas as pd
import sys

# collection = config['yoruba_collection']

def push_data(data, collection, batch_size): 
    print('Connecting to database...')

    # Connect to MongoDB
    client = MongoClient(config['client'])

    db = client["nkenne-ai"]  # Replace with your database name
    collection = db[collection]  # Replace with your collection name

    print('Connection successful!')
    print(f'Writing data to {collection} collection.')

    # Convert DataFrame to dictionary and insert into MongoDB
    documents = data.to_dict(orient="records")
    #  = 10000
    try:
        progress = 0
        total = len(documents)
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            collection.insert_many(batch)
            progress += len(batch)

            # Overwrite the same line instead of printing a new one
            sys.stdout.write(f'\r{progress}/{total} datapoints uploaded')
            sys.stdout.flush()
        print('\nData successfully loaded in the database.')
    except OperationFailure as e:
        if "over your space quota" in str(e):
            print("\nError: Storage quota exceeded. Consider cleaning up or upgrading your database.")
        else:
            print(f"\nMongoDB OperationFailure: {e}")
    finally:
        # Close the connection
        client.close()
        print("MongoDB connection closed.")


def fetch_data(collection_name, batch_size=1000, batch_number=0, query={}, projection=None):
    """
    Fetch a batch of data from a MongoDB collection using skip and limit.

    Args:
        collection_name (str): MongoDB collection name.
        batch_size (int): Number of documents per batch.
        batch_number (int): Batch number (starting from 0).
        query (dict): MongoDB query filter.
        projection (dict): Fields to return in documents.
    
    Returns:
        pd.DataFrame: DataFrame with the batch of documents.
    """
    print(f'Connecting to database for batch {batch_number}...')

    try:
        client = MongoClient(config['client'])
        db = client["nkenne-ai"]
        collection = db[collection_name]

        skip_amount = batch_size * batch_number

        cursor = collection.find(query, projection).skip(skip_amount).limit(batch_size)
        data = list(cursor)

        if data:
            df = pd.DataFrame(data)
            print(f'Fetched batch {batch_number}: {len(df)} documents.')
        else:
            df = pd.DataFrame()
            print(f'No data found in batch {batch_number}.')

        return df

    except OperationFailure as e:
        print(f"MongoDB OperationFailure: {e}")
        return pd.DataFrame()

    finally:
        client.close()
        print("MongoDB connection closed.")
