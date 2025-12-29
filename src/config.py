import os
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
DATA_DIR = PROJECT_ROOT
import json
DB_TYPE = os.getenv("DB_TYPE", "bigquery") 
DB_FILE = DATA_DIR / "cnpj_data.db"
STATUS_FILE = DATA_DIR / "ingestion_status.json"
_local_key = DATA_DIR / "service_account.json"
_secrets_key = DATA_DIR / "service_account_secrets.json"
try:
    import streamlit as st
    if "gcp_service_account" in st.secrets:
        with open(_secrets_key, "w") as f:
            json.dump(dict(st.secrets["gcp_service_account"]), f)
        GCP_CREDENTIALS_JSON = str(_secrets_key)
        GCP_CREDENTIALS_DICT = dict(st.secrets["gcp_service_account"])
        if "project_id" in st.secrets["gcp_service_account"]:
            os.environ["GCP_PROJECT_ID"] = st.secrets["gcp_service_account"]["project_id"]
    elif os.getenv("GCP_CREDENTIALS_JSON"):
         GCP_CREDENTIALS_JSON = os.getenv("GCP_CREDENTIALS_JSON")
    elif _local_key.exists():
        GCP_CREDENTIALS_JSON = str(_local_key)
    else:
        GCP_CREDENTIALS_JSON = None
        GCP_CREDENTIALS_DICT = None
except (ImportError, FileNotFoundError, Exception):
    if os.getenv("GCP_CREDENTIALS_JSON"):
        GCP_CREDENTIALS_JSON = os.getenv("GCP_CREDENTIALS_JSON")
        GCP_CREDENTIALS_DICT = None
    elif _local_key.exists():
        GCP_CREDENTIALS_JSON = str(_local_key)
        GCP_CREDENTIALS_DICT = None
    else:
        GCP_CREDENTIALS_JSON = None
        GCP_CREDENTIALS_DICT = None
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "seu-projeto-id")
BQ_DATASET = os.getenv("BQ_DATASET", "cnpj_raw")
if GCP_CREDENTIALS_JSON and (GCP_PROJECT_ID == "seu-projeto-id" or not GCP_PROJECT_ID):
    try:
        with open(GCP_CREDENTIALS_JSON, "r") as f:
            creds = json.load(f)
            if "project_id" in creds:
                GCP_PROJECT_ID = creds["project_id"]
    except Exception:
        pass
PAGE_TITLE = "Nexus Industrial Brasil"
PAGE_ICON = str(DATA_DIR / "assets" / "logo.jpg")
LAYOUT = "wide"
PROJECT_SCOPE_ONLY = True
