import streamlit as st

def render_footer():
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: grey; padding: 20px;'>
            <p>Nexus Industrial Intelligence © 2025 | Developed with Streamlit & BigQuery</p>
            <small>Data Sources: Receita Federal (CNPJ), IBGE (PIM-PF/SIDRA)</small>
        </div>
        """,
        unsafe_allow_html=True
    )
