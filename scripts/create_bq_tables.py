from google.cloud import bigquery
from google.oauth2 import service_account
import os
from src.config import GCP_PROJECT_ID, BQ_DATASET, DATA_DIR

# Configuration
# ATENÇÃO: Substitua pelo nome do SEU bucket se for diferente
BUCKET_URI = "gs://cnpj-arquivos-brutos-seunome" 
CREDENTIALS_FILE = os.path.join(DATA_DIR, "service_account.json")

def get_client():
    if os.path.exists(CREDENTIALS_FILE):
        creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
        return bigquery.Client(credentials=creds, project=GCP_PROJECT_ID)
    else:
        print(f"Erro: Arquivo {CREDENTIALS_FILE} não encontrado.")
        return None

def create_table_from_gcs():
    client = get_client()
    if not client: return

    table_id = f"{client.project}.{BQ_DATASET}.empresas"
    
    # Define Schema Manually to avoid errors
    schema = [
        bigquery.SchemaField("cnpj_basico", "STRING"),
        bigquery.SchemaField("razao_social", "STRING"),
        bigquery.SchemaField("natureza_juridica", "STRING"),
        bigquery.SchemaField("qualificacao_responsavel", "STRING"),
        bigquery.SchemaField("capital_social", "STRING"), # String because of comma/Euro format
        bigquery.SchemaField("porte_empresa", "STRING"),
        bigquery.SchemaField("ente_federativo", "STRING"),
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        skip_leading_rows=0,
        field_delimiter=";",
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE, # Replace if exists (start fresh)
        # Handle "bad" lines if necessary, though RFB is usually clean enough
        allow_quoted_newlines=True,
        encoding="ISO-8859-1"
    )

    # Point to ALL company files in bucket
    # Make sure your bucket path is correct. 
    # Example: gs://my-bucket/K3241.K03200Y*.EMPRECSV
    uri = f"{BUCKET_URI}/*.EMPRECSV"

    print(f"Iniciando criação da tabela PRINCIPAL: {table_id}...")
    print(f"Lendo arquivos de: {uri}")

    try:
        load_job = client.load_table_from_uri(
            uri, table_id, job_config=job_config
        )
        print("Job enviado. Aguardando conclusão...")
        load_job.result()
        print(f"Sucesso! Tabela Empresas criada.")
    except Exception as e:
        print(f"Erro no Load Job Empresas: {e}")

    # --- ESTABELECIMENTOS TABLE ---
    table_estab_id = f"{client.project}.{BQ_DATASET}.estabelecimentos"
    uri_estab = f"{BUCKET_URI}/*.ESTABELE"
    
    print(f"\nIniciando criação da tabela ESTABELECIMENTOS: {table_estab_id}...")
    
    # Official Layout schema
    schema_estab = [
        bigquery.SchemaField("cnpj_basico", "STRING"),
        bigquery.SchemaField("cnpj_ordem", "STRING"),
        bigquery.SchemaField("cnpj_dv", "STRING"),
        bigquery.SchemaField("identificador_matriz_filial", "STRING"),
        bigquery.SchemaField("nome_fantasia", "STRING"),
        bigquery.SchemaField("situacao_cadastral", "STRING"), # 01=Nula, 02=Ativa, 03=Suspensa, 04=Inapta, 08=Baixada
        bigquery.SchemaField("data_situacao_cadastral", "STRING"),
        bigquery.SchemaField("motivo_situacao_cadastral", "STRING"),
        bigquery.SchemaField("nome_cidade_exterior", "STRING"),
        bigquery.SchemaField("pais", "STRING"),
        bigquery.SchemaField("data_inicio_atividade", "STRING"),
        bigquery.SchemaField("cnae_fiscal_principal", "STRING"),
        bigquery.SchemaField("cnae_fiscal_secundaria", "STRING"),
        bigquery.SchemaField("tipo_logradouro", "STRING"),
        bigquery.SchemaField("logradouro", "STRING"),
        bigquery.SchemaField("numero", "STRING"),
        bigquery.SchemaField("complemento", "STRING"),
        bigquery.SchemaField("bairro", "STRING"),
        bigquery.SchemaField("cep", "STRING"),
        bigquery.SchemaField("uf", "STRING"),
        bigquery.SchemaField("municipio", "STRING"),
        bigquery.SchemaField("ddd_1", "STRING"),
        bigquery.SchemaField("telefone_1", "STRING"),
        bigquery.SchemaField("ddd_2", "STRING"),
        bigquery.SchemaField("telefone_2", "STRING"),
        bigquery.SchemaField("ddd_fax", "STRING"),
        bigquery.SchemaField("fax", "STRING"),
        bigquery.SchemaField("correio_eletronico", "STRING"),
        bigquery.SchemaField("situacao_especial", "STRING"),
        bigquery.SchemaField("data_situacao_especial", "STRING")
    ]

    job_config_estab = bigquery.LoadJobConfig(
        schema=schema_estab,
        skip_leading_rows=0, 
        field_delimiter=";",
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        allow_quoted_newlines=True,
        ignore_unknown_values=True, # Safer for large dirty datasets
        max_bad_records=10000, # Skip corrupted lines (ASCII 0, etc)
        encoding="ISO-8859-1"
    )

    try:
        load_job = client.load_table_from_uri(
            uri_estab, table_estab_id, job_config=job_config_estab
        )
        print("Job Estabelecimentos enviado. Aguardando conclusão (pode demorar)...")
        load_job.result()
        print(f"Sucesso! Tabela Estabelecimentos criada.")
    except Exception as e:
        print(f"Erro no Load Job Estabelecimentos: {e}")

    # --- REFERENCE TABLES ---
    # File suffix -> Table Name mapping
    ref_tables = [
        (".NATJUCSV", "naturezas"),
        (".MUNICCSV", "municipios"),
        (".CNAECSV", "cnaes"),
        (".MOTICSV", "motivos"),
        (".PAISCSV", "paises"),
        (".QUALSCSV", "qualificacoes")
    ]
    
    # Generic schema for most reference tables (Code;Description)
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
        encoding="ISO-8859-1"
    )

    print("\n--- Processando Tabelas de Referência ---")
    for suffix, table_name in ref_tables:
        table_ref_id = f"{client.project}.{BQ_DATASET}.{table_name}"
        uri_ref = f"{BUCKET_URI}/*{suffix}"
        
        print(f"Criando tabela: {table_name}...")
        try:
            job = client.load_table_from_uri(uri_ref, table_ref_id, job_config=ref_config)
            job.result()
            print(f"✅ {table_name} concluída.")
        except Exception as e:
            print(f"❌ Erro em {table_name}: {e}")

from google.cloud import storage

if __name__ == "__main__":
    print("--- Configuração Automática ---")
    
    # 1. Try to detect bucket automatically
    client_bq = get_client() # This returns a BQ client, but we need Storage to list
    if client_bq:
        # We need a storage client with same credentials
        if os.path.exists(CREDENTIALS_FILE):
            creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
            storage_client = storage.Client(credentials=creds, project=client_bq.project)
            
            print("Detectando bucket...")
            found = False
            try:
                for b in storage_client.list_buckets():
                    # Check for signature files
                    blobs = list(storage_client.list_blobs(b, max_results=5, prefix=""))
                    for blob in blobs:
                        if "EMPRECSV" in blob.name or "CNAECSV" in blob.name:
                            BUCKET_URI = f"gs://{b.name}"
                            print(f"-> Bucket detectado: {BUCKET_URI}")
                            found = True
                            break
                    if found: break
            except Exception as e:
                print(f"Aviso: Não foi possível listar buckets ({e}). Usando padrão do script.")
        
    print(f"Usando Bucket: {BUCKET_URI}")
    create_table_from_gcs()
