from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pathlib import Path
import streamlit as st
import json


# Prepare client secrets dynamically
client_config = {
    "installed": {
        "client_id": st.secrets["google_drive"]["client_id"],
        "client_secret": st.secrets["google_drive"]["client_secret"],
        "redirect_uris": ["http://localhost:8080/"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris":["http://localhost"]
    }
}

# Save temporary client_secrets.json
with open("client_secrets.json", "w") as f:
    json.dump(client_config, f)

# --- AUTHENTICATE ONCE GLOBALLY ---
ga = GoogleAuth()
ga.LocalWebserverAuth()
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
