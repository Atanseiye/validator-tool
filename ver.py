import streamlit as st
import pandas as pd
# import os
import json
import pymongo

import pandas as pd
import matplotlib.pyplot as plt
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import matplotlib
import pydrive
import sys


print("ver.py loaded")

# print the version of the liberary
print(f"streamlit version: {st.__version__}")
print(f"Pandas version: {pd.__version__}")
print(f"json version: {json.__version__}")
print(f"pymongo version: {pymongo.__version__}")
print(f"matplotlib version: {matplotlib.__version__}")
# print(f"pydrive version: {pydrive.__version__}")
print(f"Python version: {sys.version}")