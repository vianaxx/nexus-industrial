from google.cloud import bigquery, storage
from google.oauth2 import service_account
import os
from src.config import BQ_DATASET, GCP_CREDENTIALS_JSON

def get_clients():
    if os.path.exists(GCP_CREDENTIALS_JSON):
        creds = service_account.Credentials.from_service_account_file(GCP_CREDENTIALS_JSON)
        bq_client = bigquery.Client(credentials=creds)
        st_client = storage.Client(credentials=creds)
        return bq_client, st_client
    return None, None

def find_target_bucket(st_client):
    print("Detectando bucket com dados...")
    try:
        buckets = list(st_client.list_buckets())
        for b in buckets:
            # We look for a file "CNAECSV" inside
            blobs = list(st_client.list_blobs(b, max_results=20, prefix=""))
            for blob in blobs:
                if "CNAECSV" in blob.name:
                    print(f" -> Encontrado arquivo de dados em: {b.name}")
                    return f"gs://{b.name}"
    except Exception as e:
        print(f"Erro ao listar buckets: {e}")
    return None

def reload_references():
    bq_client, st_client = get_clients()
    if not bq_client: 
        print("Erro de credenciais.")
        return

    bucket_uri = find_target_bucket(st_client)
    if not bucket_uri:
        print("CRÍTICO: Nenhum bucket com arquivos CNPJ encontrado.")
        return

    # --- REFERENCE TABLES ---
    ref_tables = [
        (".NATJUCSV", "naturezas"),
        (".MUNICCSV", "municipios"),
        (".CNAECSV", "cnaes"),
        (".MOTICSV", "motivos"),
        (".PAISCSV", "paises"),
        (".QUALSCSV", "qualificacoes")
    ]
    
    ref_schema = [
        bigquery.SchemaField("codigo", "STRING"),
        bigquery.SchemaField("descricao", "STRING")
    ]
    
    ref_config = bigquery.LoadJobConfig(
        schema=ref_schema,
        skip_leading_rows=0, 
        field_delimiter=";",
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        allow_quoted_newlines=True,
        encoding="ISO-8859-1"  # FIX ENCODING
    )

    print(f"\n--- Recarregando Tabelas de Referência de {bucket_uri} ---")
    for suffix, table_name in ref_tables:
        table_ref_id = f"{bq_client.project}.{BQ_DATASET}.{table_name}"
        uri_ref = f"{bucket_uri}/*{suffix}"
        
        print(f"Recriando: {table_name}...")
        try:
            job = bq_client.load_table_from_uri(uri_ref, table_ref_id, job_config=ref_config)
            job.result()
            print(f"✅ {table_name} corrigida.")
        except Exception as e:
            print(f"❌ Erro em {table_name}: {e}")

if __name__ == "__main__":
    reload_references()
