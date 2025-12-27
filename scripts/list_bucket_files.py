from google.cloud import storage
from google.oauth2 import service_account
import os

CREDENTIALS_FILE = "service_account.json"
BUCKET_NAME = "cnpj-arquivos-brutos"

def list_files():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"Erro: {CREDENTIALS_FILE} não encontrado.")
        return

    try:
        creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
        client = storage.Client(credentials=creds, project=creds.project_id)
        
        bucket = client.bucket(BUCKET_NAME)
        blobs = list(bucket.list_blobs())
        
        print(f"Arquivos no bucket '{BUCKET_NAME}':")
        found_natureza = False
        for blob in blobs:
            print(f" - {blob.name}")
            if "NATJU" in blob.name:
                found_natureza = True
                
        if not found_natureza:
            print("\n❌ ALERTA: Arquivo de Naturezas (NATJU) não encontrado!")
        else:
            print("\n✅ Arquivo de Naturezas encontrado.")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    list_files()
