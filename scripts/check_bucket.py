from google.cloud import storage, bigquery
from google.oauth2 import service_account
import os
import json

# Force read configuration from file in current directory
CREDENTIALS_FILE = "service_account.json"

def check_access():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"Erro: Arquivo {CREDENTIALS_FILE} não encontrado.")
        return

    try:
        creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
        
        # 1. Check Project ID
        print(f"Acessando com Project ID: {creds.project_id}")
        
        # 2. List Buckets
        print("\n--- Listando Buckets disponíveis ---")
        storage_client = storage.Client(credentials=creds, project=creds.project_id)
        buckets = list(storage_client.list_buckets())
        
        if not buckets:
            print("Nenhum bucket encontrado neste projeto.")
        else:
            for b in buckets:
                print(f"Found Bucket: {b.name}")
                print(f"  - Location: {b.location}")
                
    except Exception as e:
        print(f"\nErro de Acesso: {e}")
        print("Dica: Verifique se a conta de serviço tem a role 'Storage Admin' ou 'Storage Object Viewer'.")

if __name__ == "__main__":
    # Install storage lib if missing
    try:
        import google.cloud.storage
    except ImportError:
        print("Instalando biblioteca storage...")
        os.system("pip install google-cloud-storage")
        print("Re-execute o script.")
        exit()
        
    check_access()
