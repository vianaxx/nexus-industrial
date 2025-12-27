import streamlit as st
import pandas as pd
import os
import glob
from ..config import DATA_DIR

def render_inspector_tab():
    st.subheader("Explorador de Arquivos")
    st.markdown("Visualize o conteúdo bruto dos arquivos CSV disponíveis na pasta.")
    
    # Use config path
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.CSV")) + glob.glob(os.path.join(DATA_DIR, "*.csv"))
    csv_files = sorted(list(set(csv_files)))
    
    if csv_files:
        selected_file = st.selectbox("Selecione um arquivo para inspecionar:", [os.path.basename(f) for f in csv_files])
        full_path = os.path.join(DATA_DIR, selected_file)
        
        # File Stats
        try:
            size_mb = os.path.getsize(full_path) / (1024 * 1024)
            st.info(f"📁 Tamanho: **{size_mb:.2f} MB**")
            
            col_count = st.number_input("Linhas para visualizar:", min_value=5, max_value=100, value=10)
            
            # Read first N lines
            df_preview = pd.read_csv(full_path, sep=';', encoding='latin-1', nrows=col_count, dtype=str)
            st.dataframe(df_preview, use_container_width=True)
            
            st.caption("Nota: Esta é apenas uma prévia das primeiras linhas do arquivo.")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")
    else:
        st.warning("Nenhum arquivo CSV encontrado na pasta.")
