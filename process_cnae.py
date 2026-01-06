import pandas as pd
import numpy as np
import os

def process():
    file_path = 'CNAE_Subclasses_2_3_Estrutura_Detalhada.xlsx'
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    print("Reading Excel...")
    # Skip rows 0-2 (Header starts row 3?) Based on previous print, Data likely starts row 4 (index 3 or 4)
    # Previous inspect showed: Row 3 (Index 3) = "A   NaN ... AGRICULTURA"
    # So skipping 3 rows means we start reading at Index 3 (Row 4).
    # Wait, read_excel(skiprows=3) means skip lines 1,2,3. Row 4 becomes Index 0.
    # Code 'A' is at Row 4.
    df = pd.read_excel(file_path, header=None, skiprows=3)
    
    # Rename columns (0-5)
    # 0: Seção, 1: Divisão, 2: Grupo, 3: Classe, 4: Subclasse, 5: Descrição
    df.columns = ['secao_code', 'divisao_code', 'grupo_code', 'classe_code', 'subclasse_code', 'desc']
    df.columns = list(df.columns[:6]) + list(df.columns[6:]) # Handle extracols if any
    
    # Extract Descriptions
    df['secao_desc'] = np.where(df['secao_code'].notna(), df['desc'], np.nan)
    df['divisao_desc'] = np.where(df['divisao_code'].notna(), df['desc'], np.nan)
    df['grupo_desc'] = np.where(df['grupo_code'].notna(), df['desc'], np.nan)
    df['classe_desc'] = np.where(df['classe_code'].notna(), df['desc'], np.nan)
    # Subclass desc is just df['desc'] when subclasse_code is notna
    
    # Fill Parent Columns
    cols_to_ffill = ['secao_code', 'secao_desc', 
                     'divisao_code', 'divisao_desc', 
                     'grupo_code', 'grupo_desc', 
                     'classe_code', 'classe_desc']
    
    df[cols_to_ffill] = df[cols_to_ffill].ffill()
    
    # Keep only Subclass rows (Leafs)
    df_clean = df[df['subclasse_code'].notna()].copy()
    
    # Project Scope: Divisions 05-33
    df_clean['div_int'] = pd.to_numeric(df_clean['divisao_code'], errors='coerce')
    df_industrial = df_clean[(df_clean['div_int'] >= 5) & (df_clean['div_int'] <= 33)].copy()
    
    # Format Labels
    # Use str() to avoid float '.0' issues if mixed types
    df_industrial['div_label'] = df_industrial['divisao_code'].astype(str).str.zfill(2) + " - " + df_industrial['divisao_desc'].astype(str)
    df_industrial['grp_label'] = df_industrial['grupo_code'].astype(str) + " - " + df_industrial['grupo_desc'].astype(str)
    df_industrial['cls_label'] = df_industrial['classe_code'].astype(str) + " - " + df_industrial['classe_desc'].astype(str)
    
    # Save
    out_path = 'src/data/cnae_hierarchy.csv'
    # Ensure dir
    os.makedirs('src/data', exist_ok=True)
    
    df_industrial.to_csv(out_path, index=False)
    print(f"Success! Saved {len(df_industrial)} rows to {out_path}")
    print("Sample:")
    print(df_industrial[['div_label', 'grp_label']].head())

if __name__ == "__main__":
    process()
