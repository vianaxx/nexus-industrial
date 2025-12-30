import os
import pandas as pd
import streamlit as st  # <--- Importante: Adicionamos isso
from google.cloud import bigquery
from google.oauth2 import service_account
from .config import GCP_PROJECT_ID, BQ_DATASET, GCP_CREDENTIALS_JSON, GCP_CREDENTIALS_DICT, PROJECT_SCOPE_ONLY
import unicodedata

class BigQueryDatabase:
    def __init__(self):
        self.project_id = GCP_PROJECT_ID
        self.dataset_id = BQ_DATASET
        self.credentials = None
        self.client = None
        
        # --- LÓGICA DE AUTENTICAÇÃO ATUALIZADA ---
        
        # 1. Tenta pegar direto das Secrets do Streamlit (Prioridade para Cloud)
        # O nome "gcp_service_account" deve ser o mesmo que você colocou no cabeçalho [gcp_service_account] nas Secrets
        if "gcp_service_account" in st.secrets:
            try:
                # Converte o objeto de secrets para um dicionário Python normal
                key_dict = dict(st.secrets["gcp_service_account"])
                
                self.credentials = service_account.Credentials.from_service_account_info(key_dict)
                
                # Se o project_id não estiver no config, tenta pegar da chave
                if not self.project_id:
                    self.project_id = key_dict.get("project_id")
                    
            except Exception as e:
                st.error(f"Erro ao ler Streamlit Secrets: {e}")

        # 2. Se não achou nas Secrets, tenta pelo dicionário do Config (Fallback)
        elif GCP_CREDENTIALS_DICT:
            self.credentials = service_account.Credentials.from_service_account_info(GCP_CREDENTIALS_DICT)
            
        # 3. Se ainda não tem credencial, tenta arquivo JSON Local (Fallback Local)
        elif GCP_CREDENTIALS_JSON:
            if os.path.exists(GCP_CREDENTIALS_JSON):
                self.credentials = service_account.Credentials.from_service_account_file(GCP_CREDENTIALS_JSON)
        
        # --- INICIALIZAÇÃO DO CLIENTE ---
        
        try:
            if self.credentials:
                self.client = bigquery.Client(credentials=self.credentials, project=self.project_id)
            else:
                # Tenta autenticação padrão (gcloud auth application-default login)
                self.client = bigquery.Client(project=self.project_id)
        except Exception as e:
            # Captura erro na inicialização do client para não quebrar o app inteiro de cara
            st.error(f"Falha ao iniciar cliente BigQuery: {e}")

    def get_total_companies(self) -> int:
        """Returns the total number of companies in the BigQuery table."""
        if not self.client: return 0
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
        """
        Searches for companies using BigQuery SQL.
        Joins with Estabelecimentos to get Status and Location (Matriz only).
        """
        if not self.client: return pd.DataFrame()

        base_query = f"""
            SELECT 
                e.cnpj_basico,
                e.razao_social,
                e.natureza_juridica,
                n.descricao as natureza_desc,
                e.qualificacao_responsavel,
                SAFE_CAST(REPLACE(e.capital_social, ',', '.') AS FLOAT64) as capital_social,
                e.porte_empresa,
                e.ente_federativo,
                st.uf,
                st.municipio,
                st.situacao_cadastral,
                st.situacao_cadastral,
                st.data_inicio_atividade,
                st.cnpj_ordem,
                st.cnpj_dv
            FROM `{self.dataset_id}.empresas` e
            LEFT JOIN `{self.dataset_id}.naturezas` n ON e.natureza_juridica = n.codigo
            LEFT JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("search_term", "STRING", f"%{query.upper()}%"),
                bigquery.ScalarQueryParameter("limit_val", "INT64", limit)
            ]
        )

        # Build WHERE clause
        where_parts = []
        
        if search_type == "name":
            where_parts.append("e.razao_social LIKE @search_term")
        else: # cnpj
            clean_query = query.replace(".", "").replace("/", "").replace("-", "")
            # Recreate param for clean query
            job_config.query_parameters[0] = bigquery.ScalarQueryParameter("search_term", "STRING", f"%{clean_query}%")
            where_parts.append("e.cnpj_basico LIKE @search_term")
            
        # CRITICAL: Enforce Project Scope (Ind. Only) in Search too
        if PROJECT_SCOPE_ONLY:
            where_parts.append("CAST(SUBSTR(st.cnae_fiscal_principal, 1, 2) AS INT64) BETWEEN 5 AND 33")

        where_cond = " AND ".join(where_parts)
        sql = f"{base_query} WHERE {where_cond} LIMIT @limit_val"
        
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_stats_natureza_juridica(self, limit: int = 10) -> pd.DataFrame:
        if not self.client: return pd.DataFrame()
        # Simplified stats (ignores status for speed)
        sql = f"""
            SELECT 
                n.descricao as nature_name,
                count(*) as count 
            FROM `{self.dataset_id}.empresas` e
            LEFT JOIN `{self.dataset_id}.naturezas` n ON e.natureza_juridica = n.codigo
            GROUP BY e.natureza_juridica, n.descricao
            ORDER BY count DESC 
            LIMIT @limit_val
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("limit_val", "INT64", limit)]
        )
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_stats_capital_social(self, limit: int = 10) -> pd.DataFrame:
        if not self.client: return pd.DataFrame()
        # Rule of thumb: Real giants are NOT '01' (ME) or '03' (EPP).
        # Petrobras is around ~200-300B. Anything above 400B is suspicious for now.
        sql = f"""
            SELECT 
                razao_social, 
                SAFE_CAST(REPLACE(capital_social, ',', '.') AS FLOAT64) as capital_social
            FROM `{self.dataset_id}.empresas` 
            WHERE SAFE_CAST(REPLACE(capital_social, ',', '.') AS FLOAT64) < 400000000000
              AND porte_empresa NOT IN ('01', '03')
            ORDER BY capital_social DESC 
            LIMIT @limit_val
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("limit_val", "INT64", limit)]
        )
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_all_naturezas(self) -> pd.DataFrame:
        if not self.client: return pd.DataFrame()
        sql = f"SELECT codigo, descricao FROM `{self.dataset_id}.naturezas` ORDER BY descricao"
        return self.client.query(sql).to_dataframe()

    def get_all_cnaes(self) -> pd.DataFrame:
        if not self.client: return pd.DataFrame()
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
        if not self.client: return pd.DataFrame()
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
        # Hardcoded for performance
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
                          cnaes=None, sectors=None, date_start=None, date_end=None, search_term=None,
                          branch_mode="Todos", limit=None):
        where_clauses = []
        
        # Search Term (Name or CNPJ)
        if search_term:
            clean_term = search_term.replace(".", "").replace("/", "").replace("-", "")
            if clean_term.isdigit():
                 # Handle Full CNPJ (14 digits) -> Extract Root (8 digits)
                 search_val = clean_term[:8] if len(clean_term) >= 8 else clean_term
                 where_clauses.append("e.cnpj_basico LIKE @search_cnpj")
                 params.append(bigquery.ScalarQueryParameter("search_cnpj", "STRING", f"%{search_val}%"))
            else:
                 where_clauses.append("e.razao_social LIKE @search_name")
                 params.append(bigquery.ScalarQueryParameter("search_name", "STRING", f"%{search_term.upper()}%"))

        # Capital Filter
        capital_expr = "SAFE_CAST(REPLACE(e.capital_social, ',', '.') AS FLOAT64)"
        if min_capital > 0:
            where_clauses.append(f"{capital_expr} >= @min_cap")
            params.append(bigquery.ScalarQueryParameter("min_cap", "FLOAT64", min_capital))
        if max_capital is not None:
            where_clauses.append(f"{capital_expr} <= @max_cap")
            params.append(bigquery.ScalarQueryParameter("max_cap", "FLOAT64", max_capital))
            
        # Porte Filter
        if portes:
            clean_portes = [p for p in portes if len(p) == 2 and p.isdigit()]
            if clean_portes:
                porte_list = ", ".join([f"'{p}'" for p in clean_portes])
                where_clauses.append(f"e.porte_empresa IN ({porte_list})")
                
        # Active Filter
        if only_active:
            where_clauses.append("st.situacao_cadastral = '02'")

        # Location Filters
        if ufs:
            uf_list = ", ".join([f"'{u}'" for u in ufs])
            where_clauses.append(f"st.uf IN ({uf_list})")
            
        if municipio_codes:
            clean_codes = [c for c in municipio_codes if c.isdigit()]
            if clean_codes:
                muni_list = ", ".join([f"'{c}'" for c in clean_codes])
                where_clauses.append(f"st.municipio IN ({muni_list})")

        # Legal Nature Filter
        if naturezas:
            clean_nats = [n for n in naturezas if n.isdigit()]
            if clean_nats:
                nat_list = ", ".join([f"'{n}'" for n in clean_nats])
                where_clauses.append(f"e.natureza_juridica IN ({nat_list})")

        # CNAE Filter
        if cnaes:
            clean_cnaes = [c for c in cnaes if c.isdigit()]
            if clean_cnaes:
                cnae_list = ", ".join([f"'{c}'" for c in clean_cnaes])
                where_clauses.append(f"st.cnae_fiscal_principal IN ({cnae_list})")

        # Sector Filter (Divisions)
        if sectors:
            clean_sectors = [s for s in sectors if len(s) == 2 and s.isdigit()]
            if clean_sectors:
                sec_list = ", ".join([f"'{s}'" for s in clean_sectors])
                where_clauses.append(f"SUBSTR(st.cnae_fiscal_principal, 1, 2) IN ({sec_list})")

        # Date Range
        if date_start:
            where_clauses.append("st.data_inicio_atividade >= @d_start")
            params.append(bigquery.ScalarQueryParameter("d_start", "STRING", date_start))
        
        if date_end:
            where_clauses.append("st.data_inicio_atividade <= @d_end")
            params.append(bigquery.ScalarQueryParameter("d_end", "STRING", date_end))
            
        # CRITICAL: Enforce Project Scope (Industrial Only)
        # Exception: If user searched specifically for something, we show it regardless of sector
        if PROJECT_SCOPE_ONLY and not search_term:
            where_clauses.append("CAST(SUBSTR(st.cnae_fiscal_principal, 1, 2) AS INT64) BETWEEN 5 AND 33")
            
        # Branch Mode Filter
        # 1 = Matriz, 2 = Filial
        if branch_mode == "Somente Matrizes":
            where_clauses.append("st.identificador_matriz_filial = '1'")
        elif branch_mode == "Somente Filiais":
            where_clauses.append("st.identificador_matriz_filial = '2'")
        # "Todos" maps to no filter (implicit 1 or 2)

        return " AND ".join(where_clauses)

    def get_filtered_companies(self, limit=100, **kwargs) -> pd.DataFrame:
        if not self.client: return pd.DataFrame()
        params = []
        if limit and limit > 0:
             params.append(bigquery.ScalarQueryParameter("limit_val", "INT64", limit))
        
        where_clause = self._build_where_clause(params, **kwargs)
        
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        limit_sql = "LIMIT @limit_val" if limit and limit > 0 else ""
            
        sql = f"""
            SELECT 
                e.cnpj_basico,
                e.razao_social, 
                e.porte_empresa,
                SAFE_CAST(REPLACE(e.capital_social, ',', '.') AS FLOAT64) as capital_social,
                e.natureza_juridica,
                n.descricao as natureza_desc,
                st.cnae_fiscal_principal,
                st.uf,
                st.municipio as municipio_codigo,
                INITCAP(m.descricao) as municipio_nome,
                st.situacao_cadastral,
                st.data_inicio_atividade,
                st.cnpj_ordem,
                st.cnpj_dv,
                st.identificador_matriz_filial
            FROM `{self.dataset_id}.empresas` e
            JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico
            LEFT JOIN `{self.dataset_id}.municipios` m ON st.municipio = m.codigo
            LEFT JOIN `{self.dataset_id}.naturezas` n ON e.natureza_juridica = n.codigo
            {where_sql}
            ORDER BY capital_social DESC
            {limit_sql}
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_opening_trend(self, **kwargs) -> pd.DataFrame:
        if not self.client: return pd.DataFrame()
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        
        sql = f"""
            SELECT 
                SUBSTR(st.data_inicio_atividade, 1, 6) as month_year,
                count(*) as count,
                ARRAY_AGG(e.razao_social LIMIT 5) as companies
            FROM `{self.dataset_id}.empresas` e
            JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico
            LEFT JOIN `{self.dataset_id}.municipios` m ON st.municipio = m.codigo
            {where_sql}
            GROUP BY month_year
            ORDER BY month_year
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_geo_distribution(self, **kwargs) -> pd.DataFrame:
        if not self.client: return pd.DataFrame()
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        
        sql = f"""
            SELECT st.uf, count(*) as count
            FROM `{self.dataset_id}.empresas` e
            JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico
            LEFT JOIN `{self.dataset_id}.municipios` m ON st.municipio = m.codigo
            {where_sql}
            GROUP BY st.uf
            ORDER BY count DESC
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_city_distribution(self, **kwargs) -> pd.DataFrame:
        if not self.client: return pd.DataFrame()
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        
        sql = f"""
            SELECT INITCAP(m.descricao) as city, count(*) as count
            FROM `{self.dataset_id}.empresas` e
            JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico
            LEFT JOIN `{self.dataset_id}.municipios` m ON st.municipio = m.codigo
            {where_sql}
            GROUP BY city
            ORDER BY count DESC
            LIMIT 10
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_sector_distribution(self, **kwargs) -> pd.DataFrame:
        if not self.client: return pd.DataFrame()
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        
        sql = f"""
            SELECT 
                SUBSTR(st.cnae_fiscal_principal, 1, 2) as sector_code,
                count(*) as count
            FROM `{self.dataset_id}.empresas` e
            JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico
            LEFT JOIN `{self.dataset_id}.municipios` m ON st.municipio = m.codigo
            {where_sql}
            GROUP BY sector_code
            ORDER BY count DESC
            LIMIT 10
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_closing_trend(self, **kwargs) -> pd.DataFrame:
        if not self.client: return pd.DataFrame()
        params = []
        # Force only_active=False to avoid conflict, we want closed ones
        kwargs['only_active'] = False
        
        where_clause = self._build_where_clause(params, **kwargs)
        base_where = f"WHERE {where_clause}" if where_clause else "WHERE 1=1"
        
        # Enforce Closed Status (08)
        full_where = f"{base_where} AND st.situacao_cadastral = '08'"
        
        sql = f"""
            SELECT 
                SUBSTR(st.data_situacao_cadastral, 1, 6) as month_year,
                count(*) as count
            FROM `{self.dataset_id}.empresas` e
            JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico
            LEFT JOIN `{self.dataset_id}.municipios` m ON st.municipio = m.codigo
            {full_where}
            GROUP BY month_year
            ORDER BY month_year
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_aggregation_metrics(self, **kwargs) -> dict:
        if not self.client: return {"count": 0, "avg_cap": 0.0}
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        
        sql = f"""
            SELECT 
                count(*) as total_count,
                avg(SAFE_CAST(REPLACE(e.capital_social, ',', '.') AS FLOAT64)) as avg_capital
            FROM `{self.dataset_id}.empresas` e
            JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico
            LEFT JOIN `{self.dataset_id}.municipios` m ON st.municipio = m.codigo
            {where_sql}
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        df = self.client.query(sql, job_config=job_config).to_dataframe()
        
        if not df.empty:
            capital = df.iloc[0]['avg_capital']
            return {
                "count": int(df.iloc[0]['total_count']),
                "avg_cap": float(capital) if pd.notnull(capital) else 0.0
            }
        return {"count": 0, "avg_cap": 0.0}

    def get_maturity_profile(self, **kwargs) -> pd.DataFrame:
        """Returns the distribution of companies by age buckets."""
        if not self.client: return pd.DataFrame()
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        
        sql = f"""
            WITH AgeData AS (
                SELECT 
                    DATE_DIFF(CURRENT_DATE(), PARSE_DATE('%Y%m%d', st.data_inicio_atividade), YEAR) as age_years
                FROM `{self.dataset_id}.empresas` e
                JOIN `{self.dataset_id}.estabelecimentos` st 
                    ON e.cnpj_basico = st.cnpj_basico
                LEFT JOIN `{self.dataset_id}.municipios` m ON st.municipio = m.codigo
                {where_sql}
            )
            SELECT
                CASE 
                    WHEN age_years < 3 THEN '1. Novas Entrantes (< 3 anos)'
                    WHEN age_years BETWEEN 3 AND 9 THEN '2. Jovens (3 a 9 anos)'
                    WHEN age_years BETWEEN 10 AND 20 THEN '3. Consolidadas (10 a 20 anos)'
                    ELSE '4. Veteranas (> 20 anos)'
                END as category,
                count(*) as count
            FROM AgeData
            GROUP BY category
            ORDER BY category
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_legal_nature_profile(self, **kwargs) -> pd.DataFrame:
        """Returns the distribution of companies by legal nature bucket."""
        if not self.client: return pd.DataFrame()
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        
        sql = f"""
            SELECT 
                CASE 
                    WHEN e.natureza_juridica LIKE '206-%' THEN 'Sociedade Limitada (LTDA)'
                    WHEN e.natureza_juridica LIKE '204-%' OR e.natureza_juridica LIKE '205-%' THEN 'S.A. (Aberta/Fechada)'
                    WHEN e.natureza_juridica LIKE '213-%' THEN 'Empresário Individual'
                    WHEN e.natureza_juridica LIKE '230-%' OR e.natureza_juridica LIKE '231-%' THEN 'Empresa Pública/MEI'
                    ELSE 'Outros'
                END as category,
                count(*) as count
            FROM `{self.dataset_id}.empresas` e
            JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico
            LEFT JOIN `{self.dataset_id}.municipios` m ON st.municipio = m.codigo
            {where_sql}
            GROUP BY category
            ORDER BY count DESC
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()
