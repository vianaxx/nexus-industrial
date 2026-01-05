import streamlit as st

def render_footer():
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: grey; padding: 20px;'>
            <p>Nexus Industrial Intelligence © 2025 | Desenvolvido com Streamlit & BigQuery</p>
            <small>Fontes de Dados: Receita Federal (CNPJ), IBGE (PIM-PF/SIDRA)</small>
        </div>
        """,
        unsafe_allow_html=True
    )
