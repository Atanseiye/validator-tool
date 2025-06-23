import streamlit as st
import pandas as pd
import shutil
import subprocess
# import os
import json
import pathlib 
import hashlib


print("ver.py loaded")

# print the version of the liberary
print(f"streamlit version: {st.__version__}")
print(f"Pandas version: {pd.__version__}")
print(f"json version: {json.__version__}")