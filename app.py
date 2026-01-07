import streamlit as st
import json
import os
import sys

# Add project root to path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import PAGE_TITLE, PAGE_ICON, LAYOUT, STATUS_FILE
from src.database import get_database
from src.ui.dashboard import (
    render_structure_filters,
    render_macro_filters,
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
        
    # --- PAGE DEFINITIONS ---
    def page_structure():
       # st.header("1. Estrutura de Mercado")
        st.markdown("---")
        filters = render_structure_filters(db)
        render_market_intelligence_view(db, filters)

    def page_macro():
       # st.header("2. Atividade Industrial")
        st.markdown("---")
        filters = render_macro_filters(db)
        render_macro_view(filters)



    # --- PAGES SETUP ---
    pg_struct = st.Page(page_structure, title="Estrutura de Mercado", icon=":material/domain:")
    pg_macro = st.Page(page_macro, title="Atividade Industrial", icon=":material/factory:")

    # --- SIDEBAR STRUCTURE (Manual Control) ---
    with st.sidebar:
        # 1. HEADER (Brand)
        st.markdown("""
        <div class="sidebar-header-container">
            <div class="sidebar-title">NEXUS INDUSTRIAL</div>
            <div class="sidebar-subtitle">
                <span style="background-color: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">BETA</span>
                <span style="margin-left: 8px;">Intelligence Suite</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        



        # 2. NAVIGATION (Custom Links using Page Objects)
        st.page_link(pg_struct, label="Estrutura de Mercado", icon=":material/domain:")
        st.page_link(pg_macro, label="Atividade Industrial", icon=":material/factory:")

        
        st.divider()
        
        with st.expander("Escopo e Metodologia"):
            st.markdown("""
            **Foco Industrial (Supply Side)**
            Monitoramos exclusivamente o núcleo produtivo nacional (CNAE 05-33):
            
            1.  **Ind. Extrativa:** Minérios, Petróleo.
            2.  **Ind. Transformação:** Manufatura.
            
            **Por que esta seleção?**
            Para isolar a *capacidade instalada* real, removendo o ruído de setores transacionais (Comércio, Serviços) ou primários (Agro).
            
            **Dados:** Base oficial da Receita Federal (CNPJ) e índices físicos do IBGE (PIM-PF).
            """)
        
    # --- NAVIGATION ROUTER (Hidden) ---
    pg = st.navigation([pg_struct, pg_macro], position="hidden")
    
    pg.run()

    # --- SIDEBAR FOOTER (Fixed at Bottom via Layout Order) ---
    with st.sidebar:

        st.markdown("""
        <div class="sidebar-footer-container">
            <div style="font-size: 0.8rem; color: #64748b;">
                <b>Fontes de Dados:</b><br>
                • Receita Federal (CNPJ)<br>
                • IBGE (PIM-PF)
            </div>
            <div style="font-size: 0.7rem; color: #94a3b8; margin-top: 8px;">
                © 2024 Nexus Intelligence
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Global Footer
    render_footer()

if __name__ == "__main__":
    main()
