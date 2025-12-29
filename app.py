import streamlit as st
import json
import os
import sys

# Add project root to path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import PAGE_TITLE, PAGE_ICON, LAYOUT, STATUS_FILE
from src.database import get_database
from src.ui.dashboard import (
    render_sidebar_filters,
    render_strategic_view, 
    render_macro_view, 
    render_market_intelligence_view
)
from src.ui.footer import render_footer
from src.ui.styles import get_custom_css
# Technical components removed for clean UI

# ...

def main():
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Inject Custom CSS
    st.markdown(get_custom_css(), unsafe_allow_html=True)

    try:
        db = get_database()
    except Exception as e:
        st.error(f"Database Initialization Error: {e}")
        st.stop()
        
    # --- SHARED SIDEBAR CONTENT (Top) ---
    with st.sidebar:
        st.title(PAGE_TITLE)
        
        # Scope Definition
        with st.expander("Escopo & Metodologia", expanded=False):
            st.markdown("""
            **Nexus Industrial Brasil**
            
            **Foco:** Indústrias Extrativas e de Transformação (CNAE Seções B e C).
            
            **Metodologia Híbrida:**
            1.  **Micro (Receita Federal):** CNPJ como *proxy* de investimento.
            2.  **Macro (IBGE):** Produção Física Oficial.
            """)
        
        # Get Filter Dict (Global) - DEFINED HERE
        filters = render_sidebar_filters(db) 
        
        st.divider()
        st.caption(f"v2.3 | {PAGE_TITLE}")

    # --- SHARED MAIN CONTENT (Search) ---
    st.markdown("## Busca Global")
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        search_query = st.text_input("Buscar Empresa ou CNPJ", placeholder="Ex: PETROBRAS, 33.000.167...", label_visibility="collapsed")
    with col_btn:
        start_btn = st.button("Pesquisar", type="primary", use_container_width=True)
    
    # Update filters with search term (Found 'filters' correctly now)
    if search_query:
        filters['search_term'] = search_query.strip()
    else:
        filters['search_term'] = None

    # Apps Tabs: Structure -> Activity -> Dynamics
    tab1, tab2, tab3 = st.tabs([
        "1. Estrutura (Mercado)", 
        "2. Atividade (Macro)", 
        "3. Dinâmica (Estratégia)"
    ])
    
    # 1. Structure (Who exists?) - DEFAULT LANDING
    with tab1:
        render_market_intelligence_view(db, filters)
    
    # 2. Activity (What is produced?)
    with tab2:
        render_macro_view(filters)
        
    with tab3:
        render_strategic_view(db, filters)

    # Global Footer
    render_footer()

if __name__ == "__main__":
    main()
