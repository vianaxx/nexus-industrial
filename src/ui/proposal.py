import streamlit as st
import pandas as pd
import altair as alt
from ..database import CNPJDatabase
from ..ibge import fetch_industry_data

def render_proposal_view(db: CNPJDatabase, filters: dict):
    st.markdown("## Estrutura Empresarial Industrial (CNPJ)")
    
    st.markdown("""
    > **Objetivo:** Apresentar a **estrutura produtiva industrial brasileira**, respondendo:
    > "Onde e como a base empresarial industrial está se organizando no território brasileiro?"
    """)

    st.divider()

    # --- BLOCO 1: KPIs de Estrutura ---
    st.subheader("🔹 1. KPIs de Estrutura")
    st.caption("Indicadores de fluxo e estoque empresarial.")

    # Fetch Data
    # 1. Active Total
    metrics = db.get_aggregation_metrics(**filters)
    total_active = metrics.get('count', 0)

    # 2. Openings (Current Year)
    # Using 'date_start' filter if set, otherwise default to current year logic? 
    # For now, let's just use the `get_opening_trend` and filter in memory for simplicity or just general trend
    df_open = db.get_opening_trend(**filters)
    
    # 3. Closings
    df_close = db.get_closing_trend(**filters)

    # Calculate Last 12 Months (L12M) or YTD stats from df
    # Let's take 'Last 12 Months' sum as a proxy for "Periodo" if no date filter
    
    open_count = 0
    close_count = 0
    
    if not df_open.empty:
        df_open['year'] = df_open['month_year'].str[:4].astype(int)
        # Sum last available year in data
        max_year = df_open['year'].max()
        open_count = df_open[df_open['year'] == max_year]['count'].sum()
        
    if not df_close.empty:
        df_close['year'] = df_close['month_year'].str[:4].astype(int)
        # Match year
        if not df_open.empty:
            close_count = df_close[df_close['year'] == max_year]['count'].sum()
        else:
             close_count = df_close['count'].sum() # Fallback

    net_balance = open_count - close_count

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estoque Ativo Total", f"{total_active:,.0f}", help="Total de CNPJs com situação 'Ativa'.")
    c2.metric("Aberturas (Último Ano)", f"{open_count:,.0f}", help="Novos CNPJs registrados no ano mais recente dos dados.")
    c3.metric("Encerramentos (Último Ano)", f"{close_count:,.0f}", delta_color="inverse", help="CNPJs baixados no ano.")
    c4.metric("Saldo Líquido", f"{net_balance:+,.0f}", help="Aberturas - Encerramentos")

    st.info("ℹ️ Estes indicadores representam a estrutura empresarial formal. Não medem produção.")

    st.divider()

    # --- BLOCO 2: Evolução Temporal ---
    st.subheader("🔹 2. Evolução Temporal da Estrutura")
    st.markdown("**Pergunta:** O investimento formal em novas unidades está acelerando?")
    
    if not df_open.empty:
        df_open['date'] = pd.to_datetime(df_open['month_year'], format='%Y%m')
        
        chart_evol = alt.Chart(df_open.tail(48)).mark_bar().encode( # Last 48 months
            x=alt.X('date:T', title='Data', axis=alt.Axis(format='%Y')),
            y=alt.Y('count:Q', title='Novos CNPJs'),
            color=alt.value('#1f77b4'),
            tooltip=['date:T', 'count']
        ).properties(height=300)
        
        st.altair_chart(chart_evol, width="stretch")
        st.caption("Nota: A data de abertura reflete o registro, podendo anteceder o início da produção.")
    else:
        st.warning("Sem dados de evolução temporal.")

    st.divider()

    # --- BLOCO 3: Distribuição Territorial ---
    st.subheader("🔹 3. Distribuição Territorial")
    st.markdown("**Pergunta:** Onde a estrutura industrial está se concentrando?")
    
    df_geo = db.get_geo_distribution(**filters)
    
    if not df_geo.empty:
        # Sort and take top 15
        df_geo_top = df_geo.sort_values('count', ascending=False).head(15)
        
        chart_map_bar = alt.Chart(df_geo_top).mark_bar().encode(
            x=alt.X('count:Q', title='Qtd Estabelecimentos'),
            y=alt.Y('uf:N', sort='-x', title='UF'),
            tooltip=['uf', 'count']
        ).properties(height=400)
        
        st.altair_chart(chart_map_bar, width="stretch")
        st.caption("A localização refere-se ao endereço cadastral.")
    else:
        st.warning("Sem dados geográficos.")

    st.divider()

    # --- BLOCO 4: Matriz x Filial ---
    st.subheader("🔹 4. Matriz x Filial (Comparativo)")
    st.markdown("**Pergunta:** A expansão é por criação de empresas ou ampliação de grupos?")
    
    # We need a custom query or Logic here.
    # We can fetch aggregation metrics TWICE with different branch_mode overrides
    
    # 1. Matrizes
    f_matriz = filters.copy()
    f_matriz['branch_mode'] = 'Somente Matrizes'
    m_matriz = db.get_aggregation_metrics(**f_matriz).get('count', 0)
    
    # 2. Filiais
    f_filial = filters.copy()
    f_filial['branch_mode'] = 'Somente Filiais'
    m_filial = db.get_aggregation_metrics(**f_filial).get('count', 0)
    
    df_comp = pd.DataFrame([
        {'Tipo': 'Matriz', 'Qtd': m_matriz},
        {'Tipo': 'Filial', 'Qtd': m_filial}
    ])
    
    chart_comp = alt.Chart(df_comp).mark_bar().encode(
        x='Qtd:Q',
        y='Tipo:N',
        color='Tipo:N',
        tooltip=['Tipo', 'Qtd']
    ).properties(height=200)
    
    st.altair_chart(chart_comp, width="stretch")
    st.caption("Filiais = Proxy de Operação | Matrizes = Localização Administrativa")
    
    st.divider()

    # --- BLOCO 5: Cruzamento com IBGE ---
    st.subheader("🔹 5. Cruzamento com Atividade (IBGE)")
    st.markdown("**Pergunta:** A produção acompanha a estrutura?")

    # Reuse Strategy View Logic but Simplified
    df_ibge = fetch_industry_data()
    
    if not df_open.empty and not df_ibge.empty:
        # Micro Data (Trend)
        df_micro = df_open.copy()
        df_micro = df_micro.groupby('date')['count'].sum()
        
        # Macro Data (Production)
        df_macro_raw = df_ibge[df_ibge['variable'].str.contains('Índice', na=False)].copy()
        df_macro = df_macro_raw.groupby('date')['value'].mean()
        
        # Align
        common = df_micro.index.intersection(df_macro.index)
        
        if len(common) > 0:
            df_scatter = pd.DataFrame({
                'date': common,
                'Abertura (CNPJ)': df_micro.loc[common].values,
                'Produção (IBGE)': df_macro.loc[common].values
            })
            
            scatter = alt.Chart(df_scatter).mark_circle(size=60).encode(
                x=alt.X('Produção (IBGE)', title='Produção (PIM-PF)'),
                y=alt.Y('Abertura (CNPJ)', title='Novos CNPJs'),
                tooltip=['date:T', 'Produção (IBGE)', 'Abertura (CNPJ)']
            ).properties(height=350)
            
            st.altair_chart(scatter, width="stretch")
            
            # Interpretação Table
            st.markdown("""
            | Produção (IBGE) | Estrutura (CNPJ) | Interpretação |
            | :--- | :--- | :--- |
            | ↑ Alta | ↑ Alta | **Expansão Real** |
            | ↑ Alta | → Estável | **Uso de Capacidade** |
            | ↓ Baixa | ↑ Alta | **Antecipação Investimento** |
            | ↓ Baixa | ↓ Baixa | **Contração** |
            """)
    else:
        st.warning("Dados insuficientes para correlação.")

    st.divider()

    # --- BLOCO 6: Linhagem de Dados (Schema) ---
    with st.expander("🔍 Espiar Estrutura do Banco (Schema & Joins)", expanded=False):
        st.markdown("""
        **Entendendo a Arquitetura de Dados (Receita Federal)**
        O dashboard unifica **4 tabelas relaccionais** para construir cada registro:
        
        1.  **EMPRESAS (Raiz):** Dados corporativos únicos por raiz (`cnpj_basico`).
            *   *Atributos:* Razão Social, Capital Social, Natureza Jurídica.
        2.  **ESTABELECIMENTOS (Unidades):** Dados da unidade física (`cnpj_basico` + `cnpj_ordem`).
            *   *Atributos:* UF, Data Abertura, Situação, Tipo (Matriz/Filial).
        3.  **MUNICPIOS (Auxiliar):** Decodifica o código do município para nome legível.
            *   *Join:* `estabelecimentos.municipio` = `municipios.codigo`
        4.  **NATUREZAS (Auxiliar):** Decodifica a natureza jurídica (ex: 206-2 Sociedade Empresária).
            *   *Join:* `empresas.natureza_juridica` = `naturezas.codigo`
        
        ---
        **Listagem Completa (Top 100 registros da seleção):**
        """)
        
        # Fetch larger sample
        safe_filters = filters.copy()
        safe_filters.pop('limit', None)
        df_sample = db.get_filtered_companies(limit=100, **safe_filters)
        
        if not df_sample.empty:
            # Format CNPJ if columns exist
            if 'cnpj_ordem' in df_sample.columns and 'cnpj_dv' in df_sample.columns:
                 # Ensure strings
                 df_sample['cnpj_basico'] = df_sample['cnpj_basico'].astype(str).str.zfill(8)
                 df_sample['cnpj_ordem'] = df_sample['cnpj_ordem'].astype(str).str.zfill(4)
                 df_sample['cnpj_dv'] = df_sample['cnpj_dv'].astype(str).str.zfill(2)
                 
                 df_sample['cnpj_real'] = (
                     df_sample['cnpj_basico'].str[:2] + "." + 
                     df_sample['cnpj_basico'].str[2:5] + "." + 
                     df_sample['cnpj_basico'].str[5:] + "/" + 
                     df_sample['cnpj_ordem'] + "-" + 
                     df_sample['cnpj_dv']
                 )
            else:
                 df_sample['cnpj_real'] = df_sample['cnpj_basico'] # Fallback
            
            # Rename columns to show Source Table
            df_disp = df_sample.rename(columns={
                'cnpj_real': '[CNPJ] Completo',
                'razao_social': '[Empresa] Razão Social',
                'capital_social': '[Empresa] Capital Social',
                'natureza_desc': '[Natureza] Descrição',
                'uf': '[Estabelecimento] UF',
                'municipio_nome': '[Município] Nome',
                'cnpj_ordem': '[Estab] Ordem (/0001)',
                'identificador_matriz_filial': '[Estab] Tipo (1/2)',
                'situacao_cadastral': '[Estab] Status'
            })
            
            st.dataframe(
                df_disp,
                width="stretch",
                column_config={
                    "[CNPJ] Completo": st.column_config.TextColumn(width="medium"),
                    "[Empresa] Capital Social": st.column_config.NumberColumn(format="R$ %.2f"),
                    "data_inicio_atividade": st.column_config.DateColumn("[Estabelecimento] Abertura", format="DD/MM/YYYY"),
                    "[Estab] Tipo (1/2)": st.column_config.TextColumn(help="1=Matriz, 2=Filial"),
                },
                column_order=[
                    "[CNPJ] Completo",
                    "[Estab] Ordem (/0001)",
                    "[Empresa] Razão Social",
                    "[Empresa] Capital Social",
                    "[Natureza] Descrição",
                    "[Município] Nome",
                    "[Estabelecimento] UF",
                    "data_inicio_atividade",
                    "[Estab] Tipo (1/2)",
                    "[Estab] Status"
                ]
            )
            st.caption(f"Visualizando os primeiros {len(df_disp)} registros encontrados com os filtros atuais.")
        else:
            st.warning("Sem dados para exibir na amostra.")

