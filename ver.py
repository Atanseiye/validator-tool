import streamlit as st
import pandas as pd
import shutil
import subprocess
# import os
import json
import pymongo
import argparse

import pandas as pd
import glob
import argparse


print("ver.py loaded")

# print the version of the liberary
print(f"streamlit version: {st.__version__}")
print(f"Pandas version: {pd.__version__}")
print(f"json version: {json.__version__}")
print(f"pymongo version: {pymongo.__version__}")