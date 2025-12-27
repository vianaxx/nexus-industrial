import requests
import pandas as pd
import streamlit as st

# IBGE SIDRA API Constants
# Tabela 8888 - PIM-PF (Produção Física)
BASE_URL = "https://servicodados.ibge.gov.br/api/v3/agregados/8888"
# 12606: Índice (Nível) | 11601: Var M/M Sazonal (Ritmo) | 11604: Outra Var (Confirmar)
# Actually, keeping safe: 
# 12606 (Index), 11601 (MoM Sazonal), 11604 (Acum 12m)
VARIABLES = "12606,11601,11604"

# Mapping CNAE Division (2 digits) -> IBGE Category ID (Table 8888)
CNAE_TO_IBGE_MAP = {
    '10': '129317', '11': '129318', '12': '129319', '13': '129320', '14': '129321',
    '15': '129322', '16': '129323', '17': '129324', '18': '129325', '19': '129326',
    '20': '56689',  '21': '129330', '22': '129331', '23': '129332', '24': '129333',
    '25': '129334', '26': '129335', '27': '129336', '28': '129337', '29': '129338',
    '30': '129339', '31': '129340', '32': '129341', '33': '129342'
}

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_industry_data(sector_code=None):
    """
    Fetches PIM-PF data from IBGE SIDRA API for Brazil and States.
    Returns a processed DataFrame.
    """
    # Determine Classification ID (General vs Specific Sector)
    class_id = '129314' # Default: Industry General
    
    if sector_code:
        # Normalize code (e.g. "10 - Food" -> "10")
        clean_code = sector_code.split(' ')[0].split('.')[0]
        class_id = CNAE_TO_IBGE_MAP.get(clean_code, '129314')
    
    # URL parameters:
    # - t=8888 (Table)
    # - n1/all (Brazil), n3/all (All States)
    # - v/all (Variables)
    # - p/last 120 (Last 10 years)
    # - c544/{class_id} (Industry Classification)
    
    url = f"{BASE_URL}/periodos/-120/variaveis/{VARIABLES}?localidades=N1[all]|N3[all]&classificacao=544[{class_id}]"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Parse data into a clean structure
        rows = []
        
        for var_item in data:
            var_id = var_item['id'] 
            
            for series_item in var_item['resultados'][0]['series']:
                location = series_item['localidade']['nome']
                series_data = series_item['serie']
                
                for date_str, value_str in series_data.items():
                    # Parse date (YYYYMM) -> Date Object
                    date = pd.to_datetime(date_str, format='%Y%m')
                    
                    try:
                        value = float(value_str)
                    except (ValueError, TypeError):
                        value = None # Handle "..." or "-" from IBGE
                        
                    rows.append({
                        'date': date,
                        'location': location,
                        'variable_id': var_id,
                        'value': value
                    })
                    
        df = pd.DataFrame(rows)
        
        if df.empty:
            return df

        # Map Variable IDs to Names (Corrected per Metadata 8888)
        var_map = {
            '12606': 'Índice Base Fixa (2022=100)',
            '12607': 'Índice Base Fixa (Sazonal)',
            '11601': 'Variação Mensal (Sazonal)',
            '11602': 'Variação Mensal (YoY)',
            '11603': 'Acumulado no Ano (YTD)',
            '11604': 'Acumulado 12 Meses (%)'
        }
        df['variable'] = df['variable_id'].map(var_map)
        
        return df.dropna(subset=['value'])
        
    except Exception as e:
        st.error(f"Erro ao buscar dados do IBGE: {e}")
        return pd.DataFrame()

def get_latest_metrics(df, location="Brasil"):
    """
    Extracts latest metrics for a specific location.
    """
    if df.empty: return {}, None
    
    loc_df = df[df['location'] == location]
    if loc_df.empty: return {}, None

    latest_date = loc_df['date'].max()
    
    # Filter for latest date
    latest = loc_df[loc_df['date'] == latest_date]
    
    latest_metrics = {}
    for _, row in latest.iterrows():
        latest_metrics[row['variable']] = row['value']
        
    return latest_metrics, latest_date
