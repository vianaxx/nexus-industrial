import sqlite3
import pandas as pd
from typing import Optional, Tuple
from .config import DB_FILE, DB_TYPE

class SQLiteDatabase:
    def __init__(self):
        self.db_path = DB_FILE

    def get_connection(self) -> sqlite3.Connection:
        if not self.db_path.exists():
           pass
        return sqlite3.connect(self.db_path)

    def get_total_companies(self) -> int:
        if not self.db_path.exists():
            return 0
            
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM empresas")
            return cursor.fetchone()[0]
        except Exception:
            return 0
        finally:
            conn.close()

    def search_companies(self, query: str, search_type: str, limit: int = 100) -> pd.DataFrame:
        conn = self.get_connection()
        try:
            base_query = """
                SELECT 
                    e.cnpj_basico,
                    e.razao_social,
                    e.natureza_juridica,
                    n.descricao as natureza_desc,
                    e.qualificacao_responsavel,
                    e.capital_social,
                    e.porte_empresa,
                    e.ente_federativo
                FROM empresas e
                LEFT JOIN naturezas n ON e.natureza_juridica = n.codigo
            """
            
            if search_type == "name":
                sql = f"{base_query} WHERE e.razao_social LIKE ? LIMIT ?"
                params = (f"%{query.upper()}%", limit)
            else:
                clean_query = query.replace(".", "").replace("/", "").replace("-", "")
                sql = f"{base_query} WHERE e.cnpj_basico LIKE ? LIMIT ?"
                params = (f"%{clean_query}%", limit)
            
            return pd.read_sql_query(sql, conn, params=params)
        finally:
            conn.close()

    def get_stats_natureza_juridica(self, limit: int = 10) -> pd.DataFrame:
        conn = self.get_connection()
        try:
            return pd.read_sql_query("""
                SELECT 
                    n.descricao as nature_name,
                    count(*) as count 
                FROM empresas e
                LEFT JOIN naturezas n ON e.natureza_juridica = n.codigo
                GROUP BY e.natureza_juridica 
                ORDER BY count DESC 
                LIMIT ?
            """, conn, params=(limit,))
        finally:
            conn.close()

    def get_stats_capital_social(self, limit: int = 10) -> pd.DataFrame:
        conn = self.get_connection()
        try:
            return pd.read_sql_query("""
                SELECT razao_social, capital_social 
                FROM empresas 
                ORDER BY capital_social DESC 
                LIMIT ?
            """, conn, params=(limit,))
        finally:
            conn.close()

def get_database():
    if DB_TYPE == "bigquery":
        from .database_bq import BigQueryDatabase
        return BigQueryDatabase()
    else:
        return SQLiteDatabase()

CNPJDatabase = get_database
