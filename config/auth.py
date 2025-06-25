from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google_auth_oauthlib.flow import Flow
from pathlib import Path
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import streamlit as st
import json
import os


# Prepare client secrets dynamically
# Dynamically build client_secrets.json content from Streamlit secrets
client_config = {
    "web": {
        "client_id": st.secrets["google_drive"]["client_id"],
        "project_id":"my-app-463810",
        "client_secret": st.secrets["google_drive"]["client_secret"],
        "auth_uri":"https://accounts.google.com/o/oauth2/auth",
        "token_uri":"https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs",
        "redirect_uris":[st.secrets["google_drive"]["redirect_uris"]],
        
    }
}

# Resolve the path one directory backwards
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
client_secrets_path = os.path.join(parent_dir, "client_secrets.json")


# Write the temporary client_secrets.json
with open(client_secrets_path, "w") as f:
    json.dump(client_config, f)

# --- AUTHENTICATE ONCE GLOBALLY ---
# ga = GoogleAuth()
# ga.LocalWebserverAuth()
# drive = GoogleDrive(ga)

ga = GoogleAuth()
ga.settings['client_config_file'] = client_secrets_path
ga.ServiceAuth()  # Use service account authentication
drive = GoogleDrive(ga)

# --- UTILITIES ---
def get_or_create_drive_folder(folder_name, parent_id=None):
    query = f"title = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    file_list = drive.ListFile({'q': query}).GetList()
    if file_list:
        return file_list[0]['id']

    folder_metadata = {
        'title': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        folder_metadata['parents'] = [{'id': parent_id}]

    folder = drive.CreateFile(folder_metadata)
    folder.Upload()
    return folder['id']

def upload_file(local_path, drive_path=None):
    local_path = Path(local_path)
    folder_id = None

    if drive_path:
        parts = Path(drive_path).parts
        for part in parts[:-1]:
            folder_id = get_or_create_drive_folder(part, parent_id=folder_id)
    
    file = drive.CreateFile({'title': parts[-1], 'parents': [{'id': folder_id}] if folder_id else []})
    file.SetContentFile(str(local_path))
    file.Upload()

def download_file(drive_path, local_path):
    parts = Path(drive_path).parts
    folder_id = None
    for part in parts[:-1]:
        folder_id = get_or_create_drive_folder(part, parent_id=folder_id)

    file_list = drive.ListFile({
        'q': f"title='{parts[-1]}' and '{folder_id}' in parents and trashed=false"
    }).GetList()
    if not file_list:
        raise FileNotFoundError(f"File '{drive_path}' not found in Google Drive")

    file_list[0].GetContentFile(local_path)

def list_files(folder_path):
    parts = Path(folder_path).parts
    folder_id = None
    for part in parts:
        folder_id = get_or_create_drive_folder(part, parent_id=folder_id)

    return drive.ListFile({
        'q': f"'{folder_id}' in parents and trashed=false"
    }).GetList()
