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
        finally:
            conn.close()
    def get_stats_capital_social(self, limit: int = 10) -> pd.DataFrame:
        conn = self.get_connection()
        try:
        finally:
            conn.close()
def get_database():
    if DB_TYPE == "bigquery":
        from .database_bq import BigQueryDatabase
        return BigQueryDatabase()
    else:
        return SQLiteDatabase()
CNPJDatabase = get_database
