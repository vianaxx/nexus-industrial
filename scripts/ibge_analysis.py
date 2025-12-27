import requests
import pandas as pd

# 1. Definição da Fonte de Dados (API IBGE - SIDRA)
# Tabela 8888: Produção Industrial (Indicadores)
URL = "https://servicodados.ibge.gov.br/api/v3/agregados/8888/periodos/-120/variaveis/12606,12607,11602?localidades=N1[all]|N3[all]&classificacao=544[129314]"

def get_ibge_dataframe():
    print(f"📡 Buscando dados em: {URL} ...")
    response = requests.get(URL)
    data = response.json()
    
    # 2. Processamento "Pythonic" dos dados JSON
    rows = []
    for var_item in data:
        var_id = var_item['id']
        var_name = ""
        if var_id == '12606': var_name = "Indice"
        elif var_id == '12607': var_name = "Var_Mensal"
        elif var_id == '11602': var_name = "Acumulado_12m"
        
        for series in var_item['resultados'][0]['series']:
            local = series['localidade']['nome']
            
            for date_key, value_str in series['serie'].items():
                # Tratamento de valores nulos ("...", "-")
                try:
                    val = float(value_str)
                except ValueError:
                    val = None
                
                rows.append({
                    "data": pd.to_datetime(date_key, format='%Y%m'),
                    "local": local,
                    "indicador": var_name,
                    "valor": val
                })

    # 3. Criação do DataFrame Pandas
    df = pd.DataFrame(rows)
    return df

if __name__ == "__main__":
    df = get_ibge_dataframe()
    
    print("\n--- 1. Visão Geral (df.info()) ---")
    print(df.info())
    
    print("\n--- 2. Primeiras Linhas (df.head()) ---")
    print(df.head())
    
    print("\n--- 3. Estatísticas Descritivas (df.describe()) ---")
    print(df.describe())
    
    print("\n--- 4. Análise Avançada: Tabela Pivot (Datas x Indicadores) ---")
    # Filtrando apenas Brasil (N1) para visualização limpa
    df_br = df[df['local'] == 'Brasil']
    pivot = df_br.pivot(index='data', columns='indicador', values='valor')
    print(pivot.tail(5)) # Últimos 5 meses
    
    print("\n--- 5. Filtro: Piores variações mensais da década ---")
    worst_months = df_br[df_br['indicador'] == 'Var_Mensal'].sort_values('valor').head(3)
    print(worst_months)
