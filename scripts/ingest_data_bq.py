import os
import glob
import time
import datetime
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from src.config import GCP_PROJECT_ID, BQ_DATASET, GCP_CREDENTIALS_JSON, DATA_DIR

# Configuration
ENCODING = 'latin-1'
BATCH_SIZE = 10000

def get_bq_client():
    if GCP_CREDENTIALS_JSON and os.path.exists(GCP_CREDENTIALS_JSON):
        credentials = service_account.Credentials.from_service_account_file(GCP_CREDENTIALS_JSON)
        return bigquery.Client(credentials=credentials, project=GCP_PROJECT_ID)
    else:
        return bigquery.Client(project=GCP_PROJECT_ID)

def create_dataset_if_not_exists(client):
    dataset_id = f"{client.project}.{BQ_DATASET}"
    try:
        client.get_dataset(dataset_id)
        print(f"Dataset {dataset_id} already exists.")
    except Exception:
        print(f"Creating dataset {dataset_id}...")
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US" # Or your preferred location
        client.create_dataset(dataset, timeout=30)
        print(f"Created dataset {dataset_id}")

def ingest_companies_bq():
    client = get_bq_client()
    create_dataset_if_not_exists(client)
    
    table_id = f"{client.project}.{BQ_DATASET}.empresas"
    
    # Define Schema
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("cnpj_basico", "STRING"),
            bigquery.SchemaField("razao_social", "STRING"),
            bigquery.SchemaField("natureza_juridica", "STRING"),
            bigquery.SchemaField("qualificacao_responsavel", "STRING"),
            bigquery.SchemaField("capital_social", "FLOAT"),
            bigquery.SchemaField("porte_empresa", "STRING"),
            bigquery.SchemaField("ente_federativo", "STRING"),
        ],
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND, # Critical: Append mode
        source_format=bigquery.SourceFormat.CSV,
    )

    files = glob.glob(os.path.join(DATA_DIR, "*EMPRECSV"))
    files = sorted(files)
    
    print(f"Found {len(files)} company files to process.")
    
    for file_path in files:
        filename = os.path.basename(file_path)
        print(f"Processing {filename}...")
        
        # We need to pre-process with pandas to handle 'capital_social' float conversion 
        # because raw CSV has European format (comma dec) and BQ expects dot or clean float.
        # Direct CSV load might fail on "1.000,00".
        
        # Using chunks to avoid memory issues
        chunk_size = 50000
        for chunk in pd.read_csv(file_path, sep=';', encoding=ENCODING, 
                                 header=None, names=[
                                     'cnpj_basico', 'razao_social', 'natureza_juridica', 
                                     'qualificacao_responsavel', 'capital_social', 
                                     'porte_empresa', 'ente_federativo'
                                 ],
                                 dtype={'cnpj_basico': str, 'natureza_juridica': str},
                                 chunksize=chunk_size):
            
            # Data Cleaning
            chunk['capital_social'] = chunk['capital_social'].astype(str).str.replace(',', '.', regex=False)
            chunk['capital_social'] = pd.to_numeric(chunk['capital_social'], errors='coerce').fillna(0.0)
            
            # Upload Chunk
            job = client.load_table_from_dataframe(
                chunk, table_id, job_config=job_config
            )
            job.result() # Wait for job to complete
            
            print(f"  Uploaded chunk of {len(chunk)} rows.")

    print("Company ingestion complete.")

def ingest_references_bq():
    client = get_bq_client()
    # Similar logic for Naturezas but REPLACE usually makes sense for dim tables
    # But user asked for Append generally. For Dimensions, usually we Replace.
    # I'll stick to Replace for dimensions as they are small and static.
    
    refs = [
        ("naturezas", "F.K03200$Z.D51213.NATJUCSV"),
        # Add municipos if needed
    ]
    
    for table_name, csv_name in refs:
        file_path = os.path.join(DATA_DIR, csv_name)
        if not os.path.exists(file_path):
            continue
            
        print(f"Ingesting {table_name}...")
        table_id = f"{client.project}.{BQ_DATASET}.{table_name}"
        
        df = pd.read_csv(file_path, sep=';', encoding=ENCODING, header=None, names=['codigo', 'descricao'], dtype=str)
        
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE, # Replace dimensions
        )
        
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        print(f"Finished {table_name}")

if __name__ == "__main__":
    print("Starting BigQuery Ingestion...")
    # ingest_references_bq() # Uncomment if needed
    ingest_companies_bq()
    print("Done.")
