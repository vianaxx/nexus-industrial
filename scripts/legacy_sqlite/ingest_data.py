import csv
import sqlite3
import os
import glob
import time
import json
import datetime

# Configuration
DATA_DIR = r"C:\Users\ercaavi\Downloads\Empresas0"
DB_FILE = os.path.join(DATA_DIR, "cnpj_data.db")
STATUS_FILE = os.path.join(DATA_DIR, "ingestion_status.json")
ENCODING = 'latin-1'

def create_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Main companies table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS empresas (
            cnpj_basico TEXT,
            razao_social TEXT,
            natureza_juridica TEXT,
            qualificacao_responsavel TEXT,
            capital_social REAL,
            porte_empresa TEXT,
            ente_federativo TEXT
        )
    """)
    
    # Reference tables
    cursor.execute("CREATE TABLE IF NOT EXISTS naturezas (codigo TEXT PRIMARY KEY, descricao TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS municipios (codigo TEXT PRIMARY KEY, descricao TEXT)")
    
    # Internal Control table for Incremental Updates
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_files (
            filename TEXT PRIMARY KEY,
            processed_at DATETIME
        )
    """)
    
    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_razao_social ON empresas(razao_social)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cnpj_basico ON empresas(cnpj_basico)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nat_juridica ON empresas(natureza_juridica)")
    
    conn.commit()
    conn.close()
    print(f"Database schema initialized/verified at {DB_FILE}")

def is_file_processed(filename):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM processed_files WHERE filename = ?", (filename,))
        return cursor.fetchone() is not None
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()

def mark_file_processed(filename):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO processed_files (filename, processed_at) VALUES (?, ?)", 
                  (filename, datetime.datetime.now()))
    conn.commit()
    conn.close()

def ingest_reference_table(filename, table_name):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Warning: Reference file {filename} not found.")
        return

    print(f"Ingesting {filename} into {table_name}...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    with open(filepath, 'r', encoding=ENCODING) as f:
        reader = csv.reader(f, delimiter=';', quotechar='"')
        batch = []
        for row in reader:
            if len(row) >= 2:
                batch.append((row[0], row[1]))
                
        cursor.executemany(f"INSERT OR REPLACE INTO {table_name} VALUES (?, ?)", batch)
        conn.commit()
    
    conn.close()
    print(f"Finished {table_name}.")

def update_status(current_file, local_rows, total_rows, start_time, status="Running"):
    elapsed = time.time() - start_time
    status_data = {
        "current_file": os.path.basename(current_file),
        "rows_processed_file": local_rows,
        "total_rows_processed": total_rows,
        "elapsed_seconds": int(elapsed),
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status
    }
    with open(STATUS_FILE, 'w') as f:
        json.dump(status_data, f)

def ingest_companies():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    files = glob.glob(os.path.join(DATA_DIR, "*EMPRECSV"))
    # Sort files to ensure deterministic order
    files = sorted(files)
    
    # Initialize status
    start_time = time.time()
    
    print(f"Found {len(files)} company files to check: {[os.path.basename(f) for f in files]}")
    
    total_processed = 0
    batch_size = 20000
    
    for i, file_path in enumerate(files):
        filename = os.path.basename(file_path)
        
        if is_file_processed(filename):
            print(f"Skipping {filename} (already processed).")
            continue

        print(f"Processing {filename}...")
        update_status(file_path, 0, total_processed, start_time)
        
        batch = []
        local_count = 0
        
        try:
            with open(file_path, 'r', encoding=ENCODING) as f:
                reader = csv.reader(f, delimiter=';', quotechar='"')
                
                for row in reader:
                    if len(row) < 7:
                        continue
                        
                    try:
                        capital = float(row[4].replace(',', '.'))
                    except ValueError:
                        capital = 0.0

                    data = (
                        row[0], # CNPJ BASICO
                        row[1], # RAZAO SOCIAL
                        row[2], # NATUREZA JURIDICA
                        row[3], # QUALIFICACAO RESP
                        capital, # CAPITAL SOCIAL
                        row[5], # PORTE
                        row[6]  # ENTE FEDERATIVO
                    )
                    
                    batch.append(data)
                    local_count += 1
                    
                    if len(batch) >= batch_size:
                        cursor.executemany("INSERT INTO empresas VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                        conn.commit()
                        total_processed += len(batch)
                        batch = []
                        print(f"  Rows: {total_processed:,}", end='\r')
                        # Update status file every batch
                        update_status(file_path, local_count, total_processed, start_time)
                
                # Remaining for this file
                if batch:
                    cursor.executemany("INSERT INTO empresas VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                    conn.commit()
                    total_processed += len(batch)
                    update_status(file_path, local_count, total_processed, start_time)
            
            # Mark as done
            mark_file_processed(filename)
                    
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            # Optional: Decide if we should stop or continue. For now, we continue.

    conn.close()
    
    # Final status
    update_status("Completed", 0, total_processed, start_time, status="Done")
        
    print(f"\nTotal new companies ingested: {total_processed:,}")

if __name__ == "__main__":
    # Ensure schema exists (including new control table)
    create_database()
    
    # Ingest References (kept as replace for updates)
    ingest_reference_table("F.K03200$Z.D51213.NATJUCSV", "naturezas")
    ingest_reference_table("F.K03200$Z.D51213.MUNICCSV", "municipios")
    
    # Ingest Companies (Incremental)
    ingest_companies()
