import os
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from .config import GCP_PROJECT_ID, BQ_DATASET, GCP_CREDENTIALS_JSON, PROJECT_SCOPE_ONLY
import unicodedata

class BigQueryDatabase:
    def __init__(self):
        self.project_id = GCP_PROJECT_ID
        self.dataset_id = BQ_DATASET
        self.credentials = None
        
        # Determine authentication method
        if GCP_CREDENTIALS_JSON:
            if os.path.exists(GCP_CREDENTIALS_JSON):
                # It's a file path
                self.credentials = service_account.Credentials.from_service_account_file(GCP_CREDENTIALS_JSON)
            else:
                # Could be JSON content string (streamlit secrets style) unfortunately service_account.Credentials.from_service_account_info takes a dict
                # For now assume file path or environment default
                pass

        if self.credentials:
            self.client = bigquery.Client(credentials=self.credentials, project=self.project_id)
        else:
            # Fallback to default env auth (useful for local dev with gcloud auth application-default login)
            self.client = bigquery.Client(project=self.project_id)
            
    def get_total_companies(self) -> int:
        """Returns the total number of companies in the BigQuery table."""
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
                st.data_inicio_atividade
            FROM `{self.dataset_id}.empresas` e
            LEFT JOIN `{self.dataset_id}.naturezas` n ON e.natureza_juridica = n.codigo
            LEFT JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico 
                AND st.identificador_matriz_filial = '1' -- Only Matriz details
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
        """Fetches all Legal Natures for UI selection."""
        sql = f"SELECT codigo, descricao FROM `{self.dataset_id}.naturezas` ORDER BY descricao"
        return self.client.query(sql).to_dataframe()

    def get_all_cnaes(self) -> pd.DataFrame:
        """Fetches all CNAEs for UI selection."""
        sql = f"SELECT codigo, descricao FROM `{self.dataset_id}.cnaes` ORDER BY descricao"
        return self.client.query(sql).to_dataframe()

    def _fetch_ibge_municipios(self) -> pd.DataFrame:
        """Fetches official municipality list (Code -> Correct Name) from IBGE API."""
        try:
            import requests
            url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                # Parse: Code (7 digits usually, but we need first 4-6 matching BQ?) 
                # BQ usually has 4 digits for 'municipio' code in Estabelecimentos?
                # Let's check schema/data. BQ 'municipios' table has 4-digit codes usually.
                # IBGE API returns 7-digit ID. The BQ 'municipios' table is likely the RFB mapping.
                # WARNING: RFB Codes != IBGE Codes directly. They are different standards.
                # Usually there is a mapping table. If we don't have it, we might be stuck.
                
                # Check: The BigQuery table `municipios` from Brasil.io/RFB usually uses SERPRO/TOM codes.
                # If so, fetching IBGE names won't match keys easily.
                # Let's try to match by NAME (Normalized) -> Correct Name.
                # Strategy: 
                # 1. Fetch IBGE list.
                # 2. Normalize IBGE names (Upper + No Accent).
                # 3. Create Map: Normalized -> Correct.
                # 4. Apply to BQ list (which is Normalized).
                
                rows = []
                for item in data:
                    name = item['nome']
                    # Simple normalization for matching key
                    norm_key = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII').upper()
                    rows.append({'normalized': norm_key, 'correct': name})
                return pd.DataFrame(rows)
        except Exception as e:
            print(f"IBGE API Error: {e}")
        return pd.DataFrame()

    def get_all_municipios(self) -> pd.DataFrame:
        """Fetches all Municipios for UI selection, enriching names via IBGE if possible."""
        # 1. Fetch Base (RFB Codes + Upper Names)
        sql = f"SELECT codigo, descricao FROM `{self.dataset_id}.municipios` ORDER BY descricao"
        df_bq = self.client.query(sql).to_dataframe()
        
        # 2. Fetch IBGE Reference
        df_ibge = self._fetch_ibge_municipios()
        
        if not df_ibge.empty and not df_bq.empty:
            # Prepare Keys for Matching
            # BQ 'descricao' is something like "SAO PAULO"
            # IBGE 'normalized' is "SAO PAULO"
            # Match!
            
            # Remove trailing spaces in BQ just in case
            df_bq['match_key'] = df_bq['descricao'].str.strip()
            
            # Merge
            merged = df_bq.merge(df_ibge, left_on='match_key', right_on='normalized', how='left')
            
            # Coalesce: Use 'correct' if found, else Title Case format of 'descricao'
            merged['final_name'] = merged['correct'].fillna(merged['descricao'].str.title())
            
            return merged[['codigo', 'final_name']].rename(columns={'final_name': 'descricao'}).sort_values('descricao')
            
        # Fallback: Just Title Case
        df_bq['descricao'] = df_bq['descricao'].str.title()
        return df_bq

    def get_industrial_divisions(self) -> pd.DataFrame:
        """Returns the 29 Industrial Divisions (CNAE Sections B & C) for high-level filtering."""
        # Hardcoded for performance and text quality (Official IBGE Names)
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
        
        # Search Term (Name or CNPJ)
        if search_term:
            # Check if it looks like a CNPJ (digits)
            clean_term = search_term.replace(".", "").replace("/", "").replace("-", "")
            if clean_term.isdigit():
                 where_clauses.append("e.cnpj_basico LIKE @search_cnpj")
                 params.append(bigquery.ScalarQueryParameter("search_cnpj", "STRING", f"%{clean_term}%"))
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
            # Filter by CODE (Exact Match)
            # Assuming codes are strings of digits
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
        if PROJECT_SCOPE_ONLY:
            # CNAE Sections B (05-09) and C (10-33)
            # This restricts ALL queries to only Extractive and Transformation Industries
            where_clauses.append("CAST(SUBSTR(st.cnae_fiscal_principal, 1, 2) AS INT64) BETWEEN 5 AND 33")

        return " AND ".join(where_clauses)

    def get_filtered_companies(self, limit=100, **kwargs) -> pd.DataFrame:
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
                st.cnae_fiscal_principal,
                st.uf,
                st.municipio as municipio_codigo,
                st.situacao_cadastral,
                st.data_inicio_atividade
            FROM `{self.dataset_id}.empresas` e
            JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico
                AND st.identificador_matriz_filial = '1'
            LEFT JOIN `{self.dataset_id}.municipios` m ON st.municipio = m.codigo
            {where_sql}
            ORDER BY capital_social DESC
            {limit_sql}
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_opening_trend(self, **kwargs) -> pd.DataFrame:
        """Aggregates companies by opening month (YYYYMM) and includes sample names."""
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
                ON e.cnpj_basico = st.cnpj_basico AND st.identificador_matriz_filial = '1'
            LEFT JOIN `{self.dataset_id}.municipios` m ON st.municipio = m.codigo
            {where_sql}
            GROUP BY month_year
            ORDER BY month_year
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_geo_distribution(self, **kwargs) -> pd.DataFrame:
        """Aggregates companies by State (UF)."""
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        
        sql = f"""
            SELECT st.uf, count(*) as count
            FROM `{self.dataset_id}.empresas` e
            JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico AND st.identificador_matriz_filial = '1'
            LEFT JOIN `{self.dataset_id}.municipios` m ON st.municipio = m.codigo
            {where_sql}
            GROUP BY st.uf
            ORDER BY count DESC
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_city_distribution(self, **kwargs) -> pd.DataFrame:
        """Aggregates companies by Municipality (Top 10)."""
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        
        # Use INITCAP on m.descricao to match our "Clean Accents" style
        sql = f"""
            SELECT INITCAP(m.descricao) as city, count(*) as count
            FROM `{self.dataset_id}.empresas` e
            JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico AND st.identificador_matriz_filial = '1'
            LEFT JOIN `{self.dataset_id}.municipios` m ON st.municipio = m.codigo
            {where_sql}
            GROUP BY city
            ORDER BY count DESC
            LIMIT 10
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_sector_distribution(self, **kwargs) -> pd.DataFrame:
        """Aggregates companies by Industrial Sector (2-digit CNAE)."""
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        
        # Note: We filter by Scope B/C in _build_where_clause, so these sectors are valid.
        sql = f"""
            SELECT 
                SUBSTR(st.cnae_fiscal_principal, 1, 2) as sector_code,
                count(*) as count
            FROM `{self.dataset_id}.empresas` e
            JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico AND st.identificador_matriz_filial = '1'
            LEFT JOIN `{self.dataset_id}.municipios` m ON st.municipio = m.codigo
            {where_sql}
            GROUP BY sector_code
            ORDER BY count DESC
            LIMIT 10
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(sql, job_config=job_config).to_dataframe()

    def get_aggregation_metrics(self, **kwargs) -> dict:
        """Calculates basic KPIs (Count, Avg Capital) in BigQuery."""
        params = []
        where_clause = self._build_where_clause(params, **kwargs)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        
        sql = f"""
            SELECT 
                count(*) as total_count,
                avg(SAFE_CAST(REPLACE(e.capital_social, ',', '.') AS FLOAT64)) as avg_capital
            FROM `{self.dataset_id}.empresas` e
            JOIN `{self.dataset_id}.estabelecimentos` st 
                ON e.cnpj_basico = st.cnpj_basico AND st.identificador_matriz_filial = '1'
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
