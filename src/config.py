import os
from pathlib import Path

# Base Paths
# Assuming this file is in src/config.py, project root is one level up
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
DATA_DIR = PROJECT_ROOT

import json

# Database Selection
# Options: "sqlite", "bigquery"
DB_TYPE = os.getenv("DB_TYPE", "bigquery") 

# Database Paths
DB_FILE = DATA_DIR / "cnpj_data.db"
STATUS_FILE = DATA_DIR / "ingestion_status.json"

# Credentials: Env Var > Local File > None (Default Auth)
# Credentials: Env Var > Local File > Streamlit Secrets > None
_local_key = DATA_DIR / "service_account.json"
_secrets_key = DATA_DIR / "service_account_secrets.json" # Temp file for ST Cloud

# Check for Streamlit Secrets (Cloud Environment)
try:
    import streamlit as st
    if "gcp_service_account" in st.secrets:
        # Write secrets to a temp file so BigQuery Client can read it as a path
        with open(_secrets_key, "w") as f:
            json.dump(dict(st.secrets["gcp_service_account"]), f)
        GCP_CREDENTIALS_JSON = str(_secrets_key)
        # Also override project_id from secrets if available
        if "project_id" in st.secrets["gcp_service_account"]:
            os.environ["GCP_PROJECT_ID"] = st.secrets["gcp_service_account"]["project_id"]
    elif os.getenv("GCP_CREDENTIALS_JSON"):
         GCP_CREDENTIALS_JSON = os.getenv("GCP_CREDENTIALS_JSON")
    elif _local_key.exists():
        GCP_CREDENTIALS_JSON = str(_local_key)
    else:
        GCP_CREDENTIALS_JSON = None
except (ImportError, FileNotFoundError, Exception):
    # Fallback for local run without streamlit or issues
    if os.getenv("GCP_CREDENTIALS_JSON"):
        GCP_CREDENTIALS_JSON = os.getenv("GCP_CREDENTIALS_JSON")
    elif _local_key.exists():
        GCP_CREDENTIALS_JSON = str(_local_key)
    else:
        GCP_CREDENTIALS_JSON = None

# BigQuery Settings
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "seu-projeto-id")
BQ_DATASET = os.getenv("BQ_DATASET", "cnpj_raw")

# Auto-detect Project ID from JSON if using placeholder
if GCP_CREDENTIALS_JSON and (GCP_PROJECT_ID == "seu-projeto-id" or not GCP_PROJECT_ID):
    try:
        with open(GCP_CREDENTIALS_JSON, "r") as f:
            creds = json.load(f)
            if "project_id" in creds:
                GCP_PROJECT_ID = creds["project_id"]
    except Exception:
        pass # Fallback to default

# UI Settings
PAGE_TITLE = "Nexus Industrial Brasil"
PAGE_ICON = None
LAYOUT = "wide"

# Scope Settings
PROJECT_SCOPE_ONLY = True # If True, restricts data to Industrial Sectors (CNAE 05-33)
