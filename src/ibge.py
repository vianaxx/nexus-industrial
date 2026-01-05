import requests
import pandas as pd
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
BASE_URL = "https://servicodados.ibge.gov.br/api/v3/agregados/8888"
VARIABLES = "12606,12607,11601,11602,11603,11604"
CNAE_TO_IBGE_MAP = {
    '10': '129317', '11': '129318', '12': '129319', '13': '129320', '14': '129321',
    '15': '129322', '16': '129323', '17': '129324', '18': '129325', '19': '129326',
    '20': '56689',  '21': '129330', '22': '129331', '23': '129332', '24': '129333',
    '25': '129334', '26': '129335', '27': '129336', '28': '129337', '29': '129338',
    '30': '129339', '31': '129340', '32': '129341', '33': '129342'
}
@st.cache_data(ttl=3600)
def fetch_industry_data(sector_code=None):
    class_id = '129314'
    if sector_code:
        clean_code = sector_code.split(' ')[0].split('.')[0]
        class_id = CNAE_TO_IBGE_MAP.get(clean_code, '129314')
    url = f"{BASE_URL}/periodos/-120/variaveis/{VARIABLES}?localidades=N1[all]|N3[all]&classificacao=544[{class_id}]"
    try:
        # Configuration for Robust Request
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        response = session.get(url, timeout=60)
        response.raise_for_status()
        data = response.json()
        rows = []
        for var_item in data:
            var_id = var_item['id'] 
            for series_item in var_item['resultados'][0]['series']:
                location = series_item['localidade']['nome']
                series_data = series_item['serie']
                for date_str, value_str in series_data.items():
                    date = pd.to_datetime(date_str, format='%Y%m')
                    try:
                        value = float(value_str)
                    except (ValueError, TypeError):
                        value = None
                    rows.append({
                        'date': date,
                        'location': location,
                        'variable_id': var_id,
                        'value': value
                    })
        df = pd.DataFrame(rows)
        if df.empty:
            return df
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
    if df.empty: return {}, None
    loc_df = df[df['location'] == location]
    if loc_df.empty: return {}, None
    latest_date = loc_df['date'].max()
    latest = loc_df[loc_df['date'] == latest_date]
    latest_metrics = {}
    for _, row in latest.iterrows():
        latest_metrics[row['variable']] = row['value']
    return latest_metrics, latest_date
