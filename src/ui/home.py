import streamlit as st
import pandas as pd
import altair as alt
from ..database import CNPJDatabase
from ..ibge import fetch_industry_data
from ..utils import format_currency

def _get_trend_icon(value):
    if value > 0.5: return "⬆️"
    if value < -0.5: return "⬇️"
    return "➡️"

def render_home_view(db: CNPJDatabase, filters: dict):
    st.markdown("# 🏠 Home Executiva")
    
    # --- FETCH DATA ---
    # 1. Macro (IBGE)
    df_ibge = fetch_industry_data()
    ibge_last = 0
    ibge_trend = 0
    
    if not df_ibge.empty:
        # Filter for General Industry Index if clear, else take mean of what's there
        # Assuming variable 'Variação Mensal' or similar exists, or calculating from Index
        # For prototype simplicity:
        latest_month = df_ibge['date'].max()
        current_data = df_ibge[df_ibge['date'] == latest_month]
        if not current_data.empty:
            ibge_last = current_data['value'].mean() # Proxy
            
        # Trend (YoY or last 12m avg)
        # Simplified: Positive last value = Growth
        ibge_trend = ibge_last

    # 2. Micro (CNPJ)
    # Totals
    metrics = db.get_aggregation_metrics(**filters)
    active_total = metrics.get('count', 0)
    
    # Flows (Open/Close) l12m
    df_open = db.get_opening_trend(**filters)
    df_close = db.get_closing_trend(**filters)
    
    open_l12m = 0
    close_l12m = 0
    
    if not df_open.empty:
        open_l12m = df_open.tail(12)['count'].sum()
    if not df_close.empty:
        close_l12m = df_close.tail(12)['count'].sum()
        
    net_balance = open_l12m - close_l12m
    
    # --- LOGIC: DETERMINE CYCLE PHASE ---
    # Logic:
    # IBGE > 0 AND Net > 0 -> Expansão
    # IBGE > 0 AND Net <= 0 -> Uso Capacidade
    # IBGE <= 0 AND Net > 0 -> Antecipação
    # IBGE <= 0 AND Net <= 0 -> Contração
    
    phase = "Indefinida"
    phase_color = "gray"
    
    if ibge_trend > 0 and net_balance > 0:
        phase = "EXPANSÃO 🚀"
        phase_color = "green"
        msg = "Crescimento simultâneo de produção e base instalada."
    elif ibge_trend > 0 and net_balance <= 0:
        phase = "USO DE CAPACIDADE 🏭"
        phase_color = "orange"
        msg = "Demanda atendida pela estrutura existente (aumento de produtividade)."
    elif ibge_trend <= 0 and net_balance > 0:
        phase = "ANTECIPAÇÃO 🏗️"
        phase_color = "blue"
        msg = "Queda na produção atual, mas investimento em novas unidades (aposta futura)."
    else:
        phase = "CONTRAÇÃO 🔻"
        phase_color = "red"
        msg = "Retração conjunta de oferta e demanda."

    # --- FAIXA 1: HEADLINE ---
    st.markdown(f"""
    <div style="padding: 20px; background-color: var(--secondary-background-color); border-left: 5px solid {phase_color}; border-radius: 5px; margin-bottom: 20px;">
        <h2 style="margin:0;">A indústria encontra-se em fase de <strong>{phase}</strong></h2>
        <p style="margin:5px 0 0 0; font-size: 1.1em;">
            Produção <b>{_get_trend_icon(ibge_trend)}</b> | 
            Estrutura Empresarial <b>{_get_trend_icon(net_balance)}</b>
        </p>
        <p style="margin-top:10px; font-size: 0.9em; opacity: 0.7;">
            <i>{msg}</i>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # --- FAIXA 2: TERMÔMETRO ---
    st.subheader("🔹 Termômetro Industrial (Últimos 12 Meses)")
    
    c1, c2, c3, c4 = st.columns(4)
    
    c1.metric("Produção Física (IBGE)", f"{ibge_last:.1f}%", "Variação L12M aproximada")
    c2.metric("Estabelecimentos Ativos", f"{active_total:,.0f}", "Estoque Total")
    c3.metric("Novas Unidades", f"{open_l12m:,.0f}", "Aberturas L12M")
    c4.metric("Saldo Líquido", f"{net_balance:+,.0f}", "Aberturas - Baixas")
    
    st.divider()

    # --- FAIXA 3: DIAGNÓSTICO INTEGRADO ---
    col_chart, col_highlights = st.columns([2, 1])
    
    with col_chart:
        st.subheader("🔹 Ciclo Industrial (Estrutura x Atividade)")
        # Reuse scatter logic simplified
        if not df_open.empty and not df_ibge.empty:
             # Just a placeholder for the verified scatter plot we built in Proposal
             # ideally we abstract this generator, but for now copying the logic for speed
             # Group by year for cleaner scatter
             df_micro = df_open.copy() # using monthly openings as proxy for structure momentum
             df_micro['date'] = pd.to_datetime(df_micro['month_year'], format='%Y%m')
             df_micro_yr = df_micro.groupby(df_micro['date'].dt.year)['count'].sum()
             
             df_macro = df_ibge.copy()
             df_macro_yr = df_macro.groupby(df_macro['date'].dt.year)['value'].mean()
             
             common = df_micro_yr.index.intersection(df_macro_yr.index)
             if len(common) > 0:
                df_cross = pd.DataFrame({
                    'Ano': common,
                    'Aberturas': df_micro_yr.loc[common].values,
                    'Produção': df_macro_yr.loc[common].values
                })
                
                chart_cycle = alt.Chart(df_cross).mark_circle(size=100).encode(
                    x=alt.X('Produção', title='Produção Média (IBGE)'),
                    y=alt.Y('Aberturas', title='Novas Unidades (CNPJ)'),
                    color='Ano:O',
                    tooltip=['Ano', 'Produção', 'Aberturas']
                ).interactive()
                
                st.altair_chart(chart_cycle, use_container_width=True)
        else:
            st.info("Dados insuficientes para plotar o ciclo histórico.")

    # --- FAIXA 4: DESTAQUES ---
    with col_highlights:
        st.subheader("🔥 Top 5 Setores (Expansão)")
        # Get sector distribution
        df_sectors = db.get_sector_distribution(**filters)
        if not df_sectors.empty:
            st.dataframe(
                df_sectors.head(5),
                column_config={
                    "sector_code": "CNAE",
                    "count": st.column_config.ProgressColumn("Qtd Unidades", format="%d")
                },
                width="stretch",
                hide_index=True
            )
        
        st.subheader("🌍 Top 5 Regiões")
        df_geo = db.get_geo_distribution(**filters)
        if not df_geo.empty:
             st.dataframe(
                df_geo.head(5),
                column_config={"uf": "Estado", "count": "Qtd"},
                width="stretch",
                hide_index=True
            )

    st.divider()
    st.caption("Para análises detalhadas, utilize as abas 'Mercado', 'Atividade' e 'Dinâmica' no topo.")
