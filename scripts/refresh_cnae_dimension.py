
import requests
import pandas as pd
import logging
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_URL = "https://servicodados.ibge.gov.br/api/v2/cnae/subclasses"
OUTPUT_PATH = "data/processed/dim_cnae.parquet"

def fetch_cnae_data():
    """Fetches full CNAE structure from IBGE API."""
    logger.info(f"Fetching data from {API_URL}...")
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched {len(data)} records.")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data: {e}")
        raise

def process_cnae_data(data):
    """Flattens the nested JSON structure into a DataFrame."""
    logger.info("Processing data...")
    
    rows = []
    for item in data:
        # Extract notes (observacoes)
        observacoes = item.get("observacoes", [])
        compreende = [obs.replace("Esta subclasse compreende - ", "").strip() for obs in observacoes if "compreende -" in obs]
        nao_compreende = [obs.replace("Esta subclasse NÃO compreende - ", "").strip() for obs in observacoes if "NÃO compreende -" in obs]
        
        # Join list items with newlines for tooltip display
        compreende_text = "\n• ".join(compreende)
        if compreende_text:
            compreende_text = "• " + compreende_text
            
        nao_compreende_text = "\n• ".join(nao_compreende)
        if nao_compreende_text:
            nao_compreende_text = "• " + nao_compreende_text

        row = {
            # Subclasse (Lowest Level)
            "id_subclasse": item["id"],
            "desc_subclasse": item["descricao"],
            "observacoes_compreende": compreende_text,
            "observacoes_nao_compreende": nao_compreende_text,
            
            # Classe
            "id_classe": item["classe"]["id"],
            "desc_classe": item["classe"]["descricao"],
            
            # Grupo
            "id_grupo": item["classe"]["grupo"]["id"],
            "desc_grupo": item["classe"]["grupo"]["descricao"],
            
            # Divisao
            "id_divisao": item["classe"]["grupo"]["divisao"]["id"],
            "desc_divisao": item["classe"]["grupo"]["divisao"]["descricao"],
            
            # Secao
            "id_secao": item["classe"]["grupo"]["divisao"]["secao"]["id"],
            "desc_secao": item["classe"]["grupo"]["divisao"]["secao"]["descricao"],
            
            # Metadata
            "data_carga": datetime.now().strftime("%Y-%m-%d")
        }
        rows.append(row)
        
    df = pd.DataFrame(rows)
    logger.info(f"Processed DataFrame shape: {df.shape}")
    return df

def save_data(df, path):
    """Saves DataFrame to Parquet."""
    logger.info(f"Saving data to {path}...")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        df.to_parquet(path, index=False)
        logger.info("Data saved successfully.")
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        # Build pandas error
        if "fastparquet" not in str(e) and "pyarrow" not in str(e):
             logger.info("Retrying with engine='pyarrow' explicitly if default failed not due to missing lib...")
             # Usually pandas auto-detects, but if it fails, it might need engine spec or installation.
             raise
        raise

if __name__ == "__main__":
    try:
        data = fetch_cnae_data()
        df = process_cnae_data(data)
        save_data(df, OUTPUT_PATH)
        print("ETL Job Completed Successfully")
    except Exception as e:
        logger.error(f"ETL Job Failed: {e}")
        exit(1)
