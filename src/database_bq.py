import os
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from .config import GCP_PROJECT_ID, BQ_DATASET, GCP_CREDENTIALS_JSON, GCP_CREDENTIALS_DICT, PROJECT_SCOPE_ONLY
import unicodedata
class BigQueryDatabase:
    def __init__(self):
        self.project_id = GCP_PROJECT_ID
        self.dataset_id = BQ_DATASET
        self.credentials = None
        if GCP_CREDENTIALS_DICT:
            self.credentials = service_account.Credentials.from_service_account_info(GCP_CREDENTIALS_DICT)
        elif GCP_CREDENTIALS_JSON:
            if os.path.exists(GCP_CREDENTIALS_JSON):
                self.credentials = service_account.Credentials.from_service_account_file(GCP_CREDENTIALS_JSON)
            else:
                pass
        if self.credentials:
            self.client = bigquery.Client(credentials=self.credentials, project=self.project_id)
        else:
            self.client = bigquery.Client(project=self.project_id)
    def get_total_companies(self) -> int:
        try:
            query = f"SELECT count(*) as count FROM `{self.dataset_id}.empresas`"
            query_job = self.client.query(query)
            results = query_job.result()
            for row in results:
                return row.count
        except Exception as e:
            print(f"BQ Error: {e}")
            return 0
    def search_companies(self, query: str, search_type: str, limit: int = 100) -> pd.DataFrame:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("search_term", "STRING", f"%{query.upper()}%"),
                bigquery.ScalarQueryParameter("limit_val", "INT64", limit)
            ]
        )
        where_parts = []
        if search_type == "name":
            where_parts.append("e.razao_social LIKE @search_term")
        else:
            clean_query = query.replace(".", "").replace("/", "").replace("-", "")
            job_config.query_parameters[0] = bigquery.ScalarQueryParameter("search_term", "STRING", f"%{clean_query}%")
            where_parts.append("e.cnpj_basico LIKE @search_term")
        if PROJECT_SCOPE_ONLY:
            where_parts.append("CAST(SUBSTR(st.cnae_fiscal_principal, 1, 2) AS INT64) BETWEEN 5 AND 33")
        where_cond = " AND ".join(where_parts)
        sql = f"{base_query} WHERE {where_cond} LIMIT @limit_val"
        return self.client.query(sql, job_config=job_config).to_dataframe()
    def get_stats_natureza_juridica(self, limit: int = 10) -> pd.DataFrame:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("limit_val", "INT64", limit)]
        )
        return self.client.query(sql, job_config=job_config).to_dataframe()
    def get_stats_capital_social(self, limit: int = 10) -> pd.DataFrame:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("limit_val", "INT64", limit)]
        )
        return self.client.query(sql, job_config=job_config).to_dataframe()
    def get_all_naturezas(self) -> pd.DataFrame:
        sql = f"SELECT codigo, descricao FROM `{self.dataset_id}.naturezas` ORDER BY descricao"
        return self.client.query(sql).to_dataframe()
    def get_all_cnaes(self) -> pd.DataFrame:
        sql = f"SELECT codigo, descricao FROM `{self.dataset_id}.cnaes` ORDER BY descricao"
        return self.client.query(sql).to_dataframe()
    def _fetch_ibge_municipios(self) -> pd.DataFrame:
        try:
            import requests
            url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                rows = []
                for item in data:
                    name = item['nome']
                    norm_key = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII').upper()
                    rows.append({'normalized': norm_key, 'correct': name})
                return pd.DataFrame(rows)
        except Exception as e:
            print(f"IBGE API Error: {e}")
        return pd.DataFrame()
    def get_all_municipios(self) -> pd.DataFrame:
        sql = f"SELECT codigo, descricao FROM `{self.dataset_id}.municipios` ORDER BY descricao"
        df_bq = self.client.query(sql).to_dataframe()
        df_ibge = self._fetch_ibge_municipios()
        if not df_ibge.empty and not df_bq.empty:
            df_bq['match_key'] = df_bq['descricao'].str.strip()
            merged = df_bq.merge(df_ibge, left_on='match_key', right_on='normalized', how='left')
            merged['final_name'] = merged['correct'].fillna(merged['descricao'].str.title())
            return merged[['codigo', 'final_name']].rename(columns={'final_name': 'descricao'}).sort_values('descricao')
        df_bq['descricao'] = df_bq['descricao'].str.title()
        return df_bq
    def get_industrial_divisions(self) -> pd.DataFrame:
        data = [
            ("05", "05 - Extração de Carvão Mineral"),
            ("06", "06 - Extração de Petróleo e Gás Natural"),
            ("07", "07 - Extração de Minerais Metálicos"),
            ("08", "08 - Extração de Minerais Não-Metálicos"),
            ("09", "09 - Atividades de Apoio à Extração de Minerais"),
            ("10", "10 - Fabricação de Produtos Alimentícios"),
            ("11", "11 - Fabricação de Bebidas"),
            ("12", "12 - Fabricação de Produtos do Fumo"),
            ("13", "13 - Fabricação de Produtos Têxteis"),
            ("14", "14 - Confecção de Artigos do Vestuário"),
            ("15", "15 - Prep. Couros e Fabricação de Artefatos de Couro"),
            ("16", "16 - Fabricação de Produtos de Madeira"),
            ("17", "17 - Fabricação de Celulose e Papel"),
            ("18", "18 - Impressão e Reprodução de Gravações"),
            ("19", "19 - Fabricação de Coque, Derivados do Petróleo e Biocombustíveis"),
            ("20", "20 - Fabricação de Produtos Químicos"),
            ("21", "21 - Fabricação de Farmoquímicos e Farmacêuticos"),
            ("22", "22 - Fabricação de Produtos de Borracha e Plástico"),
            ("23", "23 - Fabricação de Produtos de Minerais Não-Metálicos"),
            ("24", "24 - Metalurgia"),
            ("25", "25 - Fabricação de Produtos de Metal (exceto Máquinas)"),
            ("26", "26 - Fabricação de Equip. de Informática e Eletrônicos"),
            ("27", "27 - Fabricação de Máquinas e Equip. Elétricos"),
            ("28", "28 - Fabricação de Máquinas e Equipamentos"),
            ("29", "29 - Fabricação de Veículos Automotores"),
            ("30", "30 - Fabricação de Outros Equipamentos de Transporte"),
            ("31", "31 - Fabricação de Móveis"),
            ("32", "32 - Fabricação de Produtos Diversos"),
            ("33", "33 - Manutenção e Reparação de Máquinas e Equipamentos")
        ]
        return pd.DataFrame(data, columns=["division_code", "label"])
    def _build_where_clause(self, params, min_capital=0, max_capital=None, portes=None, 
                          only_active=False, ufs=None, municipio_codes=None, naturezas=None, 
                          cnaes=None, sectors=None, date_start=None, date_end=None, search_term=None):
        where_clauses = []
        if search_term:
            clean_term = search_term.replace(".", "").replace("/", "").replace("-", "")
            if clean_term.isdigit():
                 where_clauses.append("e.cnpj_basico LIKE @search_cnpj")
                 params.append(bigquery.ScalarQueryParameter("search_cnpj", "STRING", f"%{clean_term}%"))
            else:
                 where_clauses.append("e.razao_social LIKE @search_name")
                 params.append(bigquery.ScalarQueryParameter("search_name", "STRING", f"%{search_term.upper()}%"))
        capital_expr = "SAFE_CAST(REPLACE(e.capital_social, ',', '.') AS FLOAT64)"
        if min_capital > 0:
            where_clauses.append(f"{capital_expr} >= @min_cap")
            params.append(bigquery.ScalarQueryParameter("min_cap", "FLOAT64", min_capital))
        if max_capital is not None:
            where_clauses.append(f"{capital_expr} <= @max_cap")
            params.append(bigquery.ScalarQueryParameter("max_cap", "FLOAT64", max_capital))
        if portes:
            clean_portes = [p for p in portes if len(p) == 2 and p.isdigit()]
            if clean_portes:
                porte_list = ", ".join([f"'{p}'" for p in clean_portes])
                where_clauses.append(f"e.porte_empresa IN ({porte_list})")
        if only_active:
            where_clauses.append("st.situacao_cadastral = '02'")
        if ufs:
            uf_list = ", ".join([f"'{u}'" for u in ufs])
            where_clauses.append(f"st.uf IN ({uf_list})")
        if municipio_codes:
            clean_codes = [c for c in municipio_codes if c.isdigit()]
            if clean_codes:
                muni_list = ", ".join([f"'{c}'" for c in clean_codes])
                where_clauses.append(f"st.municipio IN ({muni_list})")
        if naturezas:
            clean_nats = [n for n in naturezas if n.isdigit()]
            if clean_nats:
                nat_list = ", ".join([f"'{n}'" for n in clean_nats])
                where_clauses.append(f"e.natureza_juridica IN ({nat_list})")
        if cnaes:
            clean_cnaes = [c for c in cnaes if c.isdigit()]
            if clean_cnaes:
                cnae_list = ", ".join([f"'{c}'" for c in clean_cnaes])
                where_clauses.append(f"st.cnae_fiscal_principal IN ({cnae_list})")
        if sectors:
            clean_sectors = [s for s in sectors if len(s) == 2 and s.isdigit()]
            if clean_sectors:
                sec_list = ", ".join([f"'{s}'" for s in clean_sectors])
                where_clauses.append(f"SUBSTR(st.cnae_fiscal_principal, 1, 2) IN ({sec_list})")
        if date_start:
            where_clauses.append("st.data_inicio_atividade >= @d_start")
            params.append(bigquery.ScalarQueryParameter("d_start", "STRING", date_start))
        if date_end:
            where_clauses.append("st.data_inicio_atividade <= @d_end")
            params.append(bigquery.ScalarQueryParameter("d_end", "STRING", date_end))
        if PROJECT_SCOPE_ONLY:
            where_clauses.append("CAST(SUBSTR(st.cnae_fiscal_principal, 1, 2) AS INT64) BETWEEN 5 AND 33")
        return " AND ".join(where_clauses)
    def get_filtered_companies(self, limit=100, **kwargs) -> pd.DataFrame:
        params = []
        if limit and limit > 0:
             params.append(bigquery.ScalarQueryParameter("limit_val", "INT64", limit))
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        limit_sql = "LIMIT @limit_val" if limit and limit > 0 else ""
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()
    def get_opening_trend(self, **kwargs) -> pd.DataFrame:
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()
    def get_geo_distribution(self, **kwargs) -> pd.DataFrame:
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()
    def get_city_distribution(self, **kwargs) -> pd.DataFrame:
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()
    def get_sector_distribution(self, **kwargs) -> pd.DataFrame:
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()
    def get_aggregation_metrics(self, **kwargs) -> dict:
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        df = self.client.query(sql, job_config=job_config).to_dataframe()
        if not df.empty:
            capital = df.iloc[0]['avg_capital']
            return {
                "count": int(df.iloc[0]['total_count']),
                "avg_cap": float(capital) if pd.notnull(capital) else 0.0
            }
        return {"count": 0, "avg_cap": 0.0}
