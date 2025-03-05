import json
import os

UPLOAD_INFO_FILE = "upload_info.json"

def load_upload_info():
    if os.path.exists(UPLOAD_INFO_FILE):
        try:
            with open(UPLOAD_INFO_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_upload_info(info):
    with open(UPLOAD_INFO_FILE, 'w') as f:
        json.dump(info, f, indent=2)