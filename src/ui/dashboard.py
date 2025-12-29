import streamlit as st
import pandas as pd
import altair as alt
from ..database import CNPJDatabase
from ..utils import format_cnpj, format_currency, format_date, get_status_description
from ..ibge import fetch_industry_data, get_latest_metrics

@st.cache_data
def get_options_cached(_db, method_name):
    try:
        return getattr(_db, method_name)()
    except:
        return pd.DataFrame()

def render_sidebar_filters(db: CNPJDatabase, view_mode: str = "Micro"):
    """Renders filters in sidebar and returns the filter dict.
    view_mode: 'Micro' (Default) or 'Macro'. If Macro, hides company-specific filters."""
    
    st.sidebar.divider()
    st.sidebar.header("Filtros & Segmentação")
    
    # --- SHARED FILTERS (Always Visible) ---
    
    # 1. Location
    st.sidebar.markdown("**Geografia**")
    states = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
    sel_ufs = st.sidebar.multiselect("Estados", states)
    
    # Municipality
    df_muni = get_options_cached(db, 'get_all_municipios')
    sel_city_codes = []
    
    if not df_muni.empty:
        if sel_ufs:
            muni_opts = df_muni[df_muni['uf'].isin(sel_ufs)]['descricao'].tolist() if 'uf' in df_muni.columns else df_muni['descricao'].tolist()
        else:
            muni_opts = df_muni['descricao'].tolist()
            
        sel_city_names = st.sidebar.multiselect("Municípios", muni_opts, placeholder="Selecione Cidades...")
        if sel_city_names:
            sel_city_codes = df_muni[df_muni['descricao'].isin(sel_city_names)]['codigo'].tolist()
    else:
        st.sidebar.warning("Carregando Municípios...")

    # 2. Activity
    st.sidebar.markdown("**Atividade Econômica**")
    df_sectors = get_options_cached(db, 'get_industrial_divisions')
    sel_sectors = []
    if not df_sectors.empty:
        sec_opts = df_sectors['label'].tolist()
        ui_sectors = st.sidebar.multiselect("Setores Industriais", sec_opts, placeholder="Selecione um ou mais setores...")
        sel_sectors = [s.split(" - ")[0] for s in ui_sectors]

    # Defaults for filters that might not be rendered
    
    # 3. Attributes
    st.sidebar.divider()
    st.sidebar.markdown("**Perfil da Empresa**")
    sel_portes_ui = st.sidebar.multiselect(
        "Porte", 
        ["01 (ME)", "03 (EPP)", "05 (Demais)"], 
        default=["05 (Demais)"], 
        help="**Padrão Estratégico:** Inicia focado em Médias/Grandes empresas (05) para reduzir ruído de microempresas."
    )
    if sel_portes_ui:
        sel_portes = [p.split()[0] for p in sel_portes_ui]
    else:
        sel_portes = []

    # 4. Scope
    st.sidebar.markdown("**Escopo da Visualização**")
    sel_branch_mode = st.sidebar.radio(
        "Modo de Exibição",
        ["Todos", "Somente Matrizes", "Somente Filiais"],
        index=0,
        help="**Todos:** Operação Total.\n**Matrizes:** Sede Administrativa.\n**Filiais:** Unidades Operacionais."
    )

    # 5. Advanced
    st.sidebar.markdown("**Filtros Avançados**")
    col_cap1, col_cap2 = st.sidebar.columns(2)
    min_cap = col_cap1.number_input("Min Cap", 0.0, step=10000.0)
    max_cap = col_cap2.number_input("Max Cap", 0.0, step=10000.0)
    
    date_range = st.sidebar.date_input("Data Abertura", [])
    d_start, d_end = (None, None)
    if len(date_range) == 2:
        d_start = date_range[0].strftime("%Y%m%d")
        d_end = date_range[1].strftime("%Y%m%d")

    limit = 1000 
    
    return {
        "ufs": sel_ufs, "municipio_codes": sel_city_codes, 
        "sectors": sel_sectors, "portes": sel_portes,
        "min_capital": min_cap, "max_capital": max_cap if max_cap > 0 else None,
        "only_active": True, "date_start": d_start, "date_end": d_end,
        "limit": limit, "branch_mode": sel_branch_mode
    }

def render_strategic_view(db: CNPJDatabase, filters):
    st.subheader("3. Dinâmica Industrial (Micro + Macro)")
    st.markdown("""
    **Como Evolui?**
    Aqui cruzamos a **Estrutura** (Novas Empresas) com a **Atividade** (Produção IBGE) para entender o ciclo econômico.
    *Objetivo: Identificar correlações entre investimento empresarial e produção real.*
    """)
    st.info("Comparativo entre a abertura de empresas (no seu filtro) e a Produção Industrial Nacional.")
    
    try:
        # 1. Fetch Company Trend (Micro)
        # Remove 'limit' as aggregation queries don't need it
        trend_filters = filters.copy()
        trend_filters.pop('limit', None)
        
        df_trend = db.get_opening_trend(**trend_filters)
        
        # 2. Fetch IBGE Data (Macro)
        df_ibge = fetch_industry_data()
        
        # Logic: Try Correlation -> If fails, Show Trend Only
        has_correlation = False
        
        if not df_trend.empty and not df_ibge.empty:
            # Prepare Micro Data
            df_micro = df_trend.copy()
            df_micro['date'] = pd.to_datetime(df_micro['month_year'], format='%Y%m')
            df_micro = df_micro.groupby('date')['count'].sum()
            
            # Prepare Macro Data
            df_macro_raw = df_ibge[df_ibge['variable'].str.contains('Índice', na=False)].copy()
            df_macro = df_macro_raw.groupby('date')['value'].mean()
            
            # Align
            common_idx = df_micro.index.intersection(df_macro.index).sort_values()
            
            if len(common_idx) > 6:
                has_correlation = True
                # Create ALIGNED DataFrame
                df_chart = pd.DataFrame({
                    'date': common_idx,
                    'Novas Empresas': df_micro.loc[common_idx].values,
                    'Indústria (IBGE)': df_macro.loc[common_idx].values
                })
                
                # Calculate Correlation
                corr = df_chart['Novas Empresas'].corr(df_chart['Indústria (IBGE)'])
                
                # Insight Text
                if corr > 0.7: insight = "Forte Correlação Positiva (Movimentos Idênticos)"
                elif corr < -0.7: insight = "Forte Correlação Negativa (Movimentos Opostos)"
                elif abs(corr) < 0.3: insight = "Sem Correlação Clara"
                else: insight = "Correlação Moderada"
                
                c1, c2 = st.columns([1, 3])
                c1.metric("Correlação de Pearson", f"{corr:.2f}", insight)
                
                with c1.expander("Entenda o Coeficiente"):
                    st.caption("""
                    **Pearson (r):** Mede a conexão estatística.
                    *   **+1 (Positiva):** Tendências andam juntas.
                    *   **0 (Neutra):** Sem conexão aparente.
                    *   **-1 (Negativa):** Tendências opostas.
                    """)
                
                # Dual Axis Chart
                base = alt.Chart(df_chart).encode(x='date:T')
                
                line_micro = base.mark_line(color='#ff7f0e').encode(
                    y=alt.Y('Novas Empresas', axis=alt.Axis(title='Novas Empresas', titleColor='#ff7f0e'))
                )
                
                line_macro = base.mark_line(color='#1f77b4', strokeDash=[5,5]).encode(
                    y=alt.Y('Indústria (IBGE)', axis=alt.Axis(title='Benchmark Nacional (IBGE)', titleColor='#1f77b4'))
                )
                
                st.markdown("**Como ler o gráfico:** A linha **Laranja** representa SUA SELEÇÃO (Micro). A linha **Azul** é o BENCHMARK BRASIL (Macro). Quando sobem juntas, seu setor acompanha o país.")
                
                # Combined Chart with Tooltips
                combined = (line_micro + line_macro).resolve_scale(y='independent').encode(
                    tooltip=[
                        alt.Tooltip('date:T', title='Data', format='%b/%Y'),
                        alt.Tooltip('Novas Empresas', title='Novas Empresas', format=',d'),
                        alt.Tooltip('Indústria (IBGE)', title='Indústria (idx)', format='.2f')
                    ]
                )
                st.altair_chart(combined, use_container_width=True)
                
                with st.expander("🧠 Insight Avançado: O efeito 'Time Lag'", expanded=False):
                     st.write("""
                     **Atenção:** Frequentemente existe uma defasagem (atraso) entre a abertura da empresa (linha laranja) e o início da produção (linha azul).
                     *   Fábricas demoram para ser construídas.
                     *   Se a linha laranja sobe hoje e a azul não, pode indicar **aumento de capacidade futura** (investimento em andamento).
                     """)

        if not has_correlation:
            # FALLBACK VIEW
            if not df_trend.empty:
                st.markdown("##### 🔍 Tendência de Abertura Identificada")
                
                # Prepare Data
                df_fb = df_trend.copy()
                df_fb['date'] = pd.to_datetime(df_fb['month_year'], format='%Y%m')
                
                # Process Tooltip
                if 'companies' in df_fb.columns:
                    df_fb['Empresas'] = df_fb['companies'].apply(lambda x: ", ".join(list(x)) if x is not None else "")
                else:
                    df_fb['Empresas'] = "-"

                chart_fb = alt.Chart(df_fb).mark_line(point=True, color='#ff7f0e').encode(
                    x=alt.X('date:T', title='Data'),
                    y=alt.Y('count:Q', title='Novas Empresas'),
                    tooltip=[
                        alt.Tooltip('date:T', title='Data', format='%b/%Y'), 
                        alt.Tooltip('count', title='Qtd', format=',d'),
                        alt.Tooltip('Empresas', title='Empresas')
                    ]
                ).properties(height=350)
                st.altair_chart(chart_fb, use_container_width=True)
                
                reason = "dados esparsos" if not df_trend.empty else "falta de dados"
                if df_ibge.empty: reason = "dados do IBGE indisponíveis no momento"
                
                st.info(f"""
                **Por que não vejo a Correlação?** 
                Para calcular o índice estatístico (Pearson), é necessário cruzar históricos contínuos. 
                Neste caso ({reason}), exibimos apenas a **tendência de abertura**.
                """)
            else:
                 st.warning("Sem dados suficientes para gerar visualização com os filtros atuais.")
            
    except Exception as e:
        st.error(f"Erro ao gerar visão estratégica: {e}")

UF_NAMES = {
    'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas', 'BA': 'Bahia',
    'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás',
    'MA': 'Maranhão', 'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais',
    'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná', 'PE': 'Pernambuco', 'PI': 'Piauí',
    'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte', 'RS': 'Rio Grande do Sul',
    'RO': 'Rondônia', 'RR': 'Roraima', 'SC': 'Santa Catarina', 'SP': 'São Paulo',
    'SE': 'Sergipe', 'TO': 'Tocantins'
}

def render_educational_guide():
    with st.expander("📚 Guia de Leitura: Entenda os Indicadores (SIDRA/IBGE)", expanded=False):
        st.markdown("""
        ### 1. O que significa cada coluna?
        
        | Indicador | O que mede? | Exemplo | Leitura |
        | :--- | :--- | :--- | :--- |
        | **Índice (Base Fixa)** | Nível absoluto de produção (Base 2022=100). | `108,5` | A produção está **8,5% acima** da média de 2022. Serve para comparar volumes reais ao longo do tempo. |
        | **Var. Mensal (Sazonal)** | Ritmo de curto prazo (Mês x Mês Anterior). | `2,7%` | A produção cresceu **2,7% em relação ao mês anterior**, já descontando efeitos sazonais (feriados, dias úteis). É o melhor termômetro para *inflexões*. |
        | **Var. Interanual (YoY)** | Desempenho contra mesmo mês do ano anterior. | `1,2%` | Outubro/25 vs Outubro/24. Comparação clássica de mercado, menos volátil que a mensal. |
        | **Acumulado no Ano** | Desempenho do ano corrente (Jan-Atual). | `1,0%` | "Como está o ano até agora?". Compara a soma de Jan-Out deste ano contra Jan-Out do ano passado. |
        | **Acumulado 12 Meses** | Tendência Estrutural (Longo Prazo). | `1,1%` | Últimos 12 meses vs 12 anteriores. Suaviza ruídos e mostra a direção real do ciclo. |

        ### 2. Por que vejo traços (-) ou X?
        Isso é metodologia estatística do IBGE, não erro.
        *   `-` : Zero absoluto.
        *   `X` : Dado oculto (sigilo estatístico). Ocorre quando há poucas empresas no setor/região, e divulgar o dado exporia segredos industriais.
        *   `...` : Dado não disponível ainda.
        """)

def render_macro_view(filters=None):
    st.subheader("Atividade Industrial (Macro)")
    
    # 1. Determine Intended Location
    intended_loc = "Brasil"
    is_regional_intent = False
    
    if filters and filters.get('ufs') and len(filters['ufs']) == 1:
        selected_uf = filters['ufs'][0]
        full_name = UF_NAMES.get(selected_uf)
        if full_name:
            intended_loc = full_name
            is_regional_intent = True

    # 1.5 Determine Intended Sector
    intended_sector = None
    sector_code = None
    if filters and filters.get('sectors') and len(filters['sectors']) == 1:
        intended_sector = filters['sectors'][0]
        # Assuming format "10.1 desc" or "10 desc" or just "10"
        # We need first 2 chars usually. ibge.py handles cleaning.
        sector_code = intended_sector
    
    # 2. Fetch Data & Validate Availability
    try:
        df_ibge = fetch_industry_data(sector_code)
        actual_loc = "Brasil"
        
        if not df_ibge.empty:
            if intended_loc in df_ibge['location'].unique():
                actual_loc = intended_loc
            elif is_regional_intent:
                actual_loc = "Brasil" # Fallback
        
    # 3. Render Header with ACTUAL location & Sector
        sector_display = f"do setor **{intended_sector}**" if intended_sector else "da **Indústria Geral**"
        
        st.markdown(f"""
        **O que Produz?**
        Monitoramos o volume físico produzido {sector_display} para **{actual_loc}**.
        *Esta visão serve como **Benchmark { 'Regional' if actual_loc != 'Brasil' else 'Nacional' }** de atividade.*
        """)
        
        render_educational_guide()
        
        # 4. Context/Status Messages
        if filters:
             active_msg = []
             
             # Check consistency
             is_sector_synced = (intended_sector is not None)
             is_region_synced = (is_regional_intent and actual_loc == intended_loc)
             
             if is_sector_synced and is_region_synced:
                 st.success(f"Sincronia Total: Exibindo produção de **{intended_sector}** em **{actual_loc}**.")
             elif is_sector_synced:
                 if is_regional_intent:
                     st.warning(f"Sincronia Parcial: Exibindo setor **{intended_sector}**, mas dados regionais para **{intended_loc}** não existem no IBGE. Mostrando BRASIL.")
                 else:
                     st.success(f"Sincronia Setorial: Exibindo produção nacional de **{intended_sector}**.")
             elif is_region_synced:
                 st.success(f"Sincronia Regional: Exibindo Indústria Geral de **{actual_loc}**.")
                 if filters.get('sectors'):
                     st.info(f"Nota: Vários setores selecionados. Exibindo Média Geral da Indústria.")
             else:
                 # National General Fallback
                 filter_list = []
                 if filters.get('ufs'): filter_list.append(f"Região ({', '.join(filters['ufs'])})")
                 if filters.get('sectors'): filter_list.append("Setores")
                 
                 if filter_list and not (is_sector_synced or is_region_synced):
                      st.info(f"Modo Benchmark Geral: Você filtrou por **{' + '.join(filter_list)}**, mas este gráfico exibe **Indústria Geral / Brasil**.")

        # 5. Render Charts
        if not df_ibge.empty:
            # Define Keys
            k_idx_clean = 'Índice Base Fixa (2022=100)'
            k_idx_saz = 'Índice Base Fixa (Sazonal)'
            k_mom_saz = 'Variação Mensal (Sazonal)'
            k_mom_yoy = 'Variação Mensal (YoY)'
            k_acc_year = 'Acumulado no Ano (YTD)'
            k_acc_12m = 'Acumulado 12 Meses (%)'
            
            # Keys for legacy chart support (ensure these match above)
            mom_key = k_mom_saz
            acc12_key = k_acc_12m
            idx_key = k_idx_clean

            # 1. Prepare Date Logic
            loc_df = df_ibge[df_ibge['location'] == actual_loc].copy()
            available_dates = sorted(loc_df['date'].unique(), reverse=True)
            
            selected_date = None
            if available_dates:
                # Format Dates for Dropdown
                date_opts = [d.strftime('%m/%Y') for d in available_dates]
                
                # UI: Date Selector
                c_sel, c_blank = st.columns([1, 4])
                with c_sel:
                    sel_str = st.selectbox("Selecione o Período", date_opts, index=0)
                
                # Back to logic
                selected_date = pd.to_datetime(sel_str, format='%m/%Y')
            
            # 2. Get Metrics for SELECTED Date (Manually, effectively replacing get_latest_metrics logic)
            metrics = {}
            if selected_date and not loc_df.empty:
                # Filter for selected date
                current_data = loc_df[loc_df['date'] == selected_date]
                for _, row in current_data.iterrows():
                    metrics[row['variable']] = row['value']
            
            if selected_date:
                # Prominent Reference Date Display
                ref_date_str = selected_date.strftime('%m/%Y')
                is_latest = (selected_date == available_dates[0])
                note = "(Dados mais recentes)" if is_latest else "(Histórico selecionado)"
                
            if selected_date:
                # Prominent Reference Date Display
                ref_date_str = selected_date.strftime('%m/%Y')
                is_latest = (selected_date == available_dates[0])
                note = "(Dados mais recentes)" if is_latest else "(Histórico selecionado)"
                
                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid #ff4b4b;">
                    <span style="font-size: 0.9em; font-weight: bold; color: #31333F;">Mês de Referência (IBGE):</span>
                    <span style="font-size: 1.2em; font-weight: bold; color: #000;">{ref_date_str}</span>
                    <span style="font-size: 0.8em; color: #555; margin-left: 10px;">{note} • {actual_loc}</span>
                </div>
                """, unsafe_allow_html=True)
            
            # Row 1: Structural Levels & Short Term Pulse
            c1, c2, c3 = st.columns(3)
            c1.metric("Índice (Base Fixa)", f"{metrics.get(k_idx_clean, 0):.2f}", help="Base: Média 2022 = 100")
            c2.metric("Índice (Sazonal)", f"{metrics.get(k_idx_saz, 0):.2f}", help="Ajustado sazonalmente")
            c3.metric("Var. Mensal (Sazonal)", f"{metrics.get(k_mom_saz, 0):.2f}%", help="Ritmo: Mês/Mês Anterior")
            
            # Row 2: Variations (Growth)
            c4, c5, c6 = st.columns(3)
            c4.metric("Var. Mensal (YoY)", f"{metrics.get(k_mom_yoy, 0):.2f}%", help="Mês Atual vs Mesmo Mês Ano Anterior")
            c5.metric("Acumulado no Ano", f"{metrics.get(k_acc_year, 0):.2f}%", help="Jan até Mês Atual")
            c6.metric("Acumulado 12 Meses", f"{metrics.get(k_acc_12m, 0):.2f}%", help="Tendência de Longo Prazo")
            
            # --- AUTOMATED DIAGNOSIS (Cycle Analysis) ---
            mom = metrics.get(mom_key, 0)
            acc12 = metrics.get(acc12_key, 0)
            
            if mom > 0 and acc12 > 0:
                diag_title = "FASE DE EXPANSÃO"
                diag_msg = "Resumo: O setor vive um **Ciclo Virtuoso**. O crescimento recente (Ritmo) é positivo e sustenta a alta de longo prazo (Tendência)."
                diag_type = "success"
            elif mom < 0 and acc12 > 0:
                diag_title = "FASE DE DESACELERAÇÃO"
                diag_msg = "Resumo: **Alerta Amarelo**. A tendência estrutural ainda é positiva (acumulado 12m cresce), mas o ritmo mensal perdeu força."
                diag_type = "warning"
            elif mom > 0 and acc12 < 0:
                diag_title = "FASE DE RECUPERAÇÃO"
                diag_msg = "Resumo: **Sinais de Melhora**. O setor ainda acumula perdas no longo prazo, mas o ritmo recente voltou a acelerar."
                diag_type = "info"
            else:
                diag_title = "FASE DE CONTRAÇÃO"
                diag_msg = "Resumo: **Sinal Vermelho**. Retração generalizada tanto no ritmo atual quanto no histórico de 12 meses."
                diag_type = "error"
            
            if diag_type == "success": st.success(f"**{diag_title}**\n\n{diag_msg}")
            elif diag_type == "warning": st.warning(f"**{diag_title}**\n\n{diag_msg}")
            elif diag_type == "info": st.info(f"**{diag_title}**\n\n{diag_msg}")
            else: st.error(f"**{diag_title}**\n\n{diag_msg}")
            
            # --- ANALYTICAL LAYERS (Split Charts) ---
            st.markdown("---")
            c_pulse, c_trend = st.columns(2)
            
            with c_pulse:
                st.markdown("#### O Ritmo (Curto Prazo)")
                st.caption("Variação Mensal (Sazonal)")
                with st.expander("Entenda o Ritmo"):
                    st.write("Mede a 'volatilidade'. Barras VERDES indicam aceleração mensal. Barras VERMELHAS indicam queda imediata.")
                df_pulse = df_ibge[ (df_ibge['variable'] == mom_key) & (df_ibge['location'] == actual_loc) ]
                
                bar_pulse = alt.Chart(df_pulse).mark_bar().encode(
                    x=alt.X('date:T', axis=alt.Axis(format='%Y'), title=None),
                    y=alt.Y('value:Q', title='%'),
                    color=alt.condition(alt.datum.value > 0, alt.value('#2ca02c'), alt.value('#d62728')),

                    tooltip=[
                        alt.Tooltip('date:T', title='Data', format='%b/%Y'),
                        alt.Tooltip('value', title='Variação %', format='.2f')
                    ]
                ).properties(height=250)
                st.altair_chart(bar_pulse, use_container_width=True)
                
            with c_trend:
                st.markdown("#### A Tendência (Longo Prazo)")
                st.caption("Acumulado 12 Meses")
                with st.expander("Entenda a Tendência"):
                    st.write("Mede a saúde estrutural. Remove ruídos mensais para mostrar a direção real do crescimento.")
                df_trend = df_ibge[ (df_ibge['variable'] == acc12_key) & (df_ibge['location'] == actual_loc) ]
                
                area_trend = alt.Chart(df_trend).mark_area(line={'color':'#1f77b4'}, color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='white', offset=0), alt.GradientStop(color='#1f77b4', offset=1)],
                    x1=1, x2=1, y1=1, y2=0
                ), opacity=0.5).encode(
                    x=alt.X('date:T', axis=alt.Axis(format='%Y'), title=None),
                    y=alt.Y('value:Q', title='%'),

                    tooltip=[
                        alt.Tooltip('date:T', title='Data', format='%b/%Y'),
                        alt.Tooltip('value', title='Acum. 12m %', format='.2f')
                    ]
                ).properties(height=250)
                st.altair_chart(area_trend, use_container_width=True)

            # --- NEW: ANNUAL PERFORMANCE ---
            st.markdown("---")
            c_yoy, c_year = st.columns(2)
            
            with c_yoy:
                st.markdown("#### Comparativo Anual (YoY)")
                st.caption("Variação vs Mesmo Mês Ano Anterior")
                with st.expander("Entenda o YoY"):
                    st.write("Compara outubro deste ano com outubro do ano passado. Remove o efeito sazonal comparando 'maçãs com maçãs'.")
                
                df_yoy = df_ibge[ (df_ibge['variable'] == k_mom_yoy) & (df_ibge['location'] == actual_loc) ]
                
                bar_yoy = alt.Chart(df_yoy).mark_bar().encode(
                    x=alt.X('date:T', axis=alt.Axis(format='%Y'), title=None),
                    y=alt.Y('value:Q', title='%'),
                    color=alt.condition(alt.datum.value > 0, alt.value('#2ca02c'), alt.value('#d62728')),
                    tooltip=[
                        alt.Tooltip('date:T', title='Data', format='%b/%Y'),
                        alt.Tooltip('value', title='Var. YoY %', format='.2f')
                    ]
                ).properties(height=200)
                st.altair_chart(bar_yoy, use_container_width=True)

            with c_year:
                st.markdown("#### Acumulado no Ano")
                st.caption("Janeiro até Mês de Referência")
                with st.expander("Entenda o Acumulado"):
                    st.write("Mostra o saldo do ano calendário. Se positivo, o ano está sendo de crescimento para o setor.")
                
                df_year = df_ibge[ (df_ibge['variable'] == k_acc_year) & (df_ibge['location'] == actual_loc) ]
                
                line_year = alt.Chart(df_year).mark_line(color='#9467bd').encode(
                    x=alt.X('date:T', axis=alt.Axis(format='%Y'), title=None),
                    y=alt.Y('value:Q', title='%'),
                    tooltip=[
                        alt.Tooltip('date:T', title='Data', format='%b/%Y'),
                        alt.Tooltip('value', title='Acum. Ano %', format='.2f')
                    ]
                ).properties(height=200)
                st.altair_chart(line_year, use_container_width=True)

            st.markdown("---")
            st.markdown("---")
            st.markdown(f"#### Nível da Atividade - {actual_loc} (Estrutural)")
            st.caption("Índice de Base Fixa (2022=100)")
            with st.expander("Entenda o Nível"):
                st.write("Mostra o tamanho real da produção. Se a linha está acima de 100, produziu mais que na média de 2022. Compare com o Brasil para ver competitividade.")

            # Filter Data for Chart (Compare Regional vs National) - LEVEL ONLY
            valid_locs = [actual_loc]
            
            # Optional Comparison
            if actual_loc != "Brasil":
                show_benchmark = st.checkbox("Comparar com Benchmark Nacional 🇧🇷", value=False, help="Sobrepõe a curva de Nível do Brasil para comparação.")
                if show_benchmark:
                    valid_locs.append("Brasil")
            
            # Filter Level Data
            df_chart = df_ibge[ (df_ibge['variable'] == idx_key) & (df_ibge['location'].isin(valid_locs)) ].copy()
            
            # Dynamic Encoding
            base_chart = alt.Chart(df_chart).mark_line(point=True)
            
            if len(valid_locs) > 1:
                # Comparative Mode
                chart_ibge = base_chart.encode(
                    x=alt.X('date:T', title='Data', axis=alt.Axis(format='%Y')),
                    y=alt.Y('value:Q', title='Índice (2022=100)', scale=alt.Scale(zero=False)),
                    color=alt.value('#FF8C00'), # Orange for main line isn't ideal for comparison logic. relying on strokeDash
                    strokeDash=alt.StrokeDash('location', title='Local', legend=alt.Legend(orient='bottom')),
                    tooltip=[
                        alt.Tooltip('date:T', title='Data', format='%b/%Y'),
                        alt.Tooltip('value', title='Índice', format='.2f'),
                        alt.Tooltip('location', title='Local')
                    ]
                )
            else:
                # Clean Mode
                chart_ibge = base_chart.encode(
                    x=alt.X('date:T', title='Data', axis=alt.Axis(format='%Y')),
                    y=alt.Y('value:Q', title='Índice (2022=100)', scale=alt.Scale(zero=False)),
                    tooltip=[
                        alt.Tooltip('date:T', title='Data', format='%b/%Y'),
                        alt.Tooltip('value', title='Índice', format='.2f')
                    ]
                )

            chart_ibge = chart_ibge.properties(height=400).interactive()
            st.altair_chart(chart_ibge, use_container_width=True)

            # --- PRO LEVEL: SCATTER & RANKING ---
            st.markdown("---")
            st.subheader("Diagnóstico Estrutural (Visão Panorâmica)")
            st.markdown("Onde sua seleção se encaixa no cenário nacional? Compare com outros estados/setores.")
            
            # Prepare Data for Scatter/Ranking (Latest Snapshot of ALL locations present in data)
            latest_date_all = df_ibge['date'].max()
            df_snapshot = df_ibge[df_ibge['date'] == latest_date_all].copy()
            
            if not df_snapshot.empty:
                # Pivot: index=location, columns=variable, values=value
                # Need to handle potential duplicates if multiple sectors? 
                # df_ibge usually filtered by ONE sector code in fetch logic. 
                # So 'location' is the only differentiator.
                df_pivot = df_snapshot.pivot(index='location', columns='variable', values='value').reset_index()
                
                # Check columns existence
                if mom_key in df_pivot.columns and acc12_key in df_pivot.columns:
                    c_scat, c_rank = st.columns([3, 2])
                    
                    with c_scat:
                        st.markdown("**Mapa de Ciclo Econômico**", help="Divide os estados em 4 quadrantes:\n- Expansão (Dir/Sup): Crescendo rápido e sólido.\n- Desaceleração (Dir/Inf): Tendência positiva, mas ritmo caindo.\n- Recuperação (Esq/Sup): Reagindo mês a mês, mas ainda negativo no ano.\n- Contração (Esq/Inf): Queda generalizada.")
                        st.caption(f"Posicionamento dos Estados/Regiões em {latest_date_all.strftime('%m/%Y')}")
                        
                        # Base Chart
                        base_scat = alt.Chart(df_pivot).mark_circle(size=120, opacity=0.8).encode(
                            x=alt.X(acc12_key, title='Tendência (Acum. 12m %)', axis=alt.Axis(grid=False)),
                            y=alt.Y(mom_key, title='Ritmo (Var. Mensal %)', axis=alt.Axis(grid=False)),
                            color=alt.condition(
                                alt.datum.location == actual_loc, 
                                alt.value('#d62728'),  # Red for selection
                                alt.value('lightgray') # Gray for context
                            ),

                            tooltip=[
                                alt.Tooltip('location', title='Local'),
                                alt.Tooltip(acc12_key, title='Tendência (12m)', format='.2f'),
                                alt.Tooltip(mom_key, title='Ritmo (Mensal)', format='.2f')
                            ]
                        ).properties(height=400)
                        
                        # Labels
                        text_scat = base_scat.mark_text(align='left', dx=8, fontSize=11).encode(
                            text='location',
                            color=alt.value('black')
                        )
                        
                        # Quadrant Lines (Zero)
                        rule_x = alt.Chart(pd.DataFrame({'x': [0]})).mark_rule(color='gray', strokeDash=[5,5]).encode(x='x')
                        rule_y = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(color='gray', strokeDash=[5,5]).encode(y='y')
                        
                        # Render Composite
                        st.altair_chart((base_scat + text_scat + rule_x + rule_y).interactive(), use_container_width=True)
                        
                        st.caption("• **Sup. Direito:** Expansão | • **Sup. Esquerdo:** Recuperação | • **Inf. Direito:** Desaceleração | • **Inf. Esquerdo:** Contração")
                        
                    with c_rank:
                        st.markdown("**Ranking de Desempenho (12m)**")
                        st.caption("Quem está crescendo mais?")
                        
                        rank_chart = alt.Chart(df_pivot).mark_bar().encode(
                            x=alt.X(acc12_key, title='%', axis=alt.Axis(grid=False)),
                            y=alt.Y('location', sort='-x', title=None),
                            color=alt.condition(
                                alt.datum.location == actual_loc,
                                alt.value('#d62728'),
                                alt.value('#1f77b4') 
                            ),

                            tooltip=[
                                alt.Tooltip('location', title='Local'),
                                alt.Tooltip(acc12_key, title='Crescimento (12m)', format='.2f')
                            ]
                        ).properties(height=400)
                        
                        st.altair_chart(rank_chart, use_container_width=True)
                else:
                    st.info("Dados insuficientes para gerar o Mapa de Ciclo (Scatter).")
        else:
            st.warning("Dados do IBGE indisponíveis no momento.")

    except Exception as e:
        st.error(f"Erro ao carregar dados macro: {e}")

def render_methodology_view():
    st.subheader("4. Framework Metodológico (Conceito)")
    
    st.markdown("""
    Esta seção documenta a lógica analítica utilizada neste dashboard, permitindo auditoria e alinhamento conceitual.
    
    ---
    
    ### 1. Papel Analítico dos Dados
    
    | Fonte | Papel no Dashboard | O que responde? |
    | :--- | :--- | :--- |
    | **CNPJ (Receita Federal)** | **Estrutura Produtiva** | Quem são os players? Onde estão? Estão expandindo (abrindo filiais)? |
    | | | Formato: `AA.AAA.AAA/BBBB-CC` (onde `/0001`=Matriz e `/0002+`=Filial) |
    | **IBGE (PIM-PF)** | **Atividade Real** | Quanto foi produzido? O ritmo está acelerando ou caindo? Qual a tendência? |
    
    > *Erro comum a evitar: Confundir CNPJ (registro burocrático) com Produção (volume físico). CNPJ é capacidade potencial; IBGE é realização.*
    
    ---

    ### 2. Modos de Leitura (Matriz vs. Filial)
    
    #### 🔹 Estrutura Técnica do CNPJ
    Cada registro possui 14 dígitos organizados no formato `AA.AAA.AAA/BBBB-CC`:
    
    *   `AA.AAA.AAA` → **CNPJ Raiz (`cnpj_basico`)**: Identifica a empresa.
    *   `BBBB` → **Ordem (`cnpj_ordem`)**: Identifica o estabelecimento.
        *   `0001` → Geralmente a **Matriz**.
        *   `0002`, `0003`... → **Filiais**.
    *   `CC` → **Dígito Verificador (`cnpj_dv`)**.

    #### 🔹 Como identificamos no Banco de Dados?
    Utilizamos o campo oficial `identificador_matriz_filial`:
    *   Valor `1` → **Matriz** (Sede administrativa/jurídica).
    *   Valor `2` → **Filial** (Unidade operacional, fábrica, cd, etc).

    > **⚠️ Atenção (Caso Especial/Fusões):**
    > Nem toda Matriz é `/0001`. Em casos de fusão, aquisição ou reestruturação (como no caso da Lactalis), a sede pode assumir outro número (ex: `/0054`).
    > **O que vale para o dashboard é o campo "Tipo" (Status 1), não o número do sufixo.**

    ---

    #### 💡 As Três "Lentes" do Dashboard:

    #### 1. Todos os Estabelecimentos (Global)
    *   **Lógica:** Soma de Matrizes (1) + Filiais (2).
    *   **O que mostra:** A pegada física total da indústria no território.

    #### 2. Somente Matrizes (Corporativo)
    *   **Lógica:** Filtro `identificador_matriz_filial = '1'`.
    *   **O que mostra:** Onde estão os *decision makers* e o domicílio fiscal.

    #### 3. Somente Filiais (Operacional)
    *   **Lógica:** Filtro `identificador_matriz_filial = '2'`.
    *   **O que mostra:** Onde a produção e a operação física realmente acontecem (fábricas longe da sede).

    ---

    ### 3. Matriz de Decisão Integrada (O "Pulo do Gato")
    Como cruzar os sinais do IBGE com os sinais do CNPJ para gerar insights de investimento:

    | Cenário IBGE (Produção) | Cenário CNPJ (Filiais) | Diagnóstico Provável |
    | :---: | :---: | :--- |
    | 📈 **Crescendo** | 📈 **Crescendo** | **Expansão Real:** O mercado demanda mais, e as empresas estão investindo em nova capacidade para atender. |
    | 📈 **Crescendo** | ➡️ **Estável** | **Uso de Capacidade:** A demanda subiu, mas a indústria está atendendo com as fábricas que já existem (aumento de turnos/ocupação). |
    | 📉 **Caindo** | 📈 **Crescendo** | **Aposta Futura (ou Defasagem):** A produção está ruim hoje, mas empresas estão abrindo filiais. Pode indicar *novos entrantes* ou *projetos de longo prazo* maturando. |
    | 📉 **Caindo** | 📉 **Caindo** | **Crise Estrutural:** Retração tanto na saída (vendas) quanto no investimento (fechamento de unidades). |

    ---

    ### 4. Limitações Declaradas
    *   **Natureza:** CNPJ é um dado cadastral. Não informa faturamento real nem número de funcionários atualizado em tempo real.
    *   **Proxy:** Usamos "Filiais" como proxy de fábrica, mas uma filial pode ser apenas um escritório de vendas ou galpão logístico. A análise assume que, na agregação (Lei dos Grandes Números), o movimento de filiais industriais segue a lógica produtiva.
    """)

def render_market_intelligence_view(db: CNPJDatabase, filters):
    # CSS: Card Style for Metrics
    st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05); /* Subtle background */
        border: 1px solid rgba(128, 128, 128, 0.2);  /* Subtle border */
        padding: 15px;                                /* Spacing */
        border-radius: 8px;                           /* Rounded corners */
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);       /* Soft shadow */
    }
    </style>
    """, unsafe_allow_html=True)

    st.subheader("Estrutura de Mercado (Micro)")
    st.markdown("""
    **Quem são os Players?**
    Análise fundamentalista da base instalada (CNPJ). 
    *Foco: Market Share, Concentração Geográfica e Solidez Financeira.*
    """)
    
    # Methodological Knowledge Base

    
    
    # Methodological Knowledge Base
    
    
    
    with st.spinner("Processando Big Data..."):
        try:
            # 1. Prepare Data
            mi_filters = filters.copy()
            
            # Fetch Aggregates (Full) & Sample (Table)
            # POP limit so it doesn't break get_sector_distribution kwargs
            limit = mi_filters.pop('limit', 1000)
            
            # --- HYBRID KPI LOGIC ---
            # 1. View Scope (User Selection): Used for "Total Analyzed" (Count)
            # Reflects the number of operational units (Matrices + Branches if selected)
            metrics_view = db.get_aggregation_metrics(**mi_filters)
            true_total = metrics_view.get('count', 0)
            
            # 2. Financial Scope (Strictly Matrices): Used for "Average Capital"
            # Always measures the financial strength of the unique Companies (Headquarters),
            # avoiding duplication or dilution by branches.
            filters_fin = mi_filters.copy()
            filters_fin['branch_mode'] = 'Somente Matrizes'
            metrics_fin = db.get_aggregation_metrics(**filters_fin)
            true_avg_cap = metrics_fin.get('avg_cap', 0.0)
            
            # 3. Visuals (Limited)
            df_sectors = db.get_sector_distribution(**mi_filters)

            # Revert to standard fetching (User wants to see Branches grouped in main table)
            df_companies = db.get_filtered_companies(limit=limit, **mi_filters) # Sample with Limit

            # OPTIMIZATION: Client-Side Enrichment (De-normalized codes -> Text)
            if not df_companies.empty:
                 df_nat = get_options_cached(db, 'get_all_naturezas')
                 df_cnae = get_options_cached(db, 'get_all_cnaes')
                 df_muni = get_options_cached(db, 'get_all_municipios')

                 # Natureza: DB now returns 'natureza_desc', so check before merging
                 if 'natureza_desc' not in df_companies.columns:
                     if not df_nat.empty and 'natureza_juridica' in df_companies.columns:
                         df_companies = df_companies.merge(df_nat, left_on='natureza_juridica', right_on='codigo', how='left').rename(columns={'descricao': 'natureza_desc'})
                
                 if not df_cnae.empty and 'cnae_fiscal_principal' in df_companies.columns:
                     df_companies = df_companies.merge(df_cnae, left_on='cnae_fiscal_principal', right_on='codigo', how='left').rename(columns={'descricao': 'cnae_desc'})

                 # Municipio: DB returns 'municipio_nome', UI expects 'municipio'
                 if 'municipio_nome' in df_companies.columns:
                      df_companies['municipio'] = df_companies['municipio_nome']
                 
                 if 'municipio' not in df_companies.columns:
                      if not df_muni.empty and 'municipio_codigo' in df_companies.columns:
                          df_companies = df_companies.merge(df_muni, left_on='municipio_codigo', right_on='codigo', how='left').rename(columns={'descricao': 'municipio'})
            
            if df_companies.empty:
                st.warning("Nenhum player encontrado com os filtros atuais.")
                return

            # Format CNPJ if columns exist (Global Standard)
            if 'cnpj_ordem' in df_companies.columns and 'cnpj_dv' in df_companies.columns:
                 # Ensure strings
                 df_companies['cnpj_basico'] = df_companies['cnpj_basico'].astype(str).str.zfill(8)
                 df_companies['cnpj_ordem'] = df_companies['cnpj_ordem'].astype(str).str.zfill(4)
                 df_companies['cnpj_dv'] = df_companies['cnpj_dv'].astype(str).str.zfill(2)
                 
                 df_companies['cnpj_real'] = (
                     df_companies['cnpj_basico'].str[:2] + "." + 
                     df_companies['cnpj_basico'].str[2:5] + "." + 
                     df_companies['cnpj_basico'].str[5:] + "/" + 
                     df_companies['cnpj_ordem'] + "-" + 
                     df_companies['cnpj_dv']
                 )
            else:
                 df_companies['cnpj_real'] = df_companies['cnpj_basico'] # Fallback

            # 2. Financial Terminal Header (KPIs)
            
            # Helper to calc share
            total_mkt = true_total if true_total > 0 else 1
            
            # Market Concentration (Herfindahl Proxy - Share of Top 1 Sector)
            concentration = 0
            leader_name = "-"
            if not df_sectors.empty:
                top_sec = df_sectors.iloc[0]
                concentration = (top_sec['count'] / total_mkt) * 100
                leader_name = top_sec['sector_code']

            st.markdown("#### Key Performance Indicators")
            k1, k2, k3, k4 = st.columns(4)
            # Format US (Standard)
            fmt_total = f"{true_total:,.0f}" # e.g. 1,000
            
            # Smart Currency Format (US Standard)
            if true_avg_cap >= 1e9:
                # Billions: R$ 1.50 B
                val_fmt = f"{true_avg_cap/1e9:,.2f}"
                fmt_cap_display = f"R$ {val_fmt} B"
            elif true_avg_cap >= 1e6:
                # Millions: R$ 2.50 MM
                val_fmt = f"{true_avg_cap/1e6:,.2f}"
                fmt_cap_display = f"R$ {val_fmt} MM"
            else:
                # Standard: R$ 1,500.00
                fmt_cap_display = f"R$ {true_avg_cap:,.2f}"

            # Dynamic Tooltip Logic for Sector KPI
            branch_mode = mi_filters.get('branch_mode', 'Todos')
            
            if branch_mode == 'Somente Matrizes':
                tooltip_sector = """**Setor Dominante (Estrutura Corporativa)**

Indica a Divisão Industrial (CNAE – 2 dígitos) com maior número de empresas-matriz ativas.

Neste modo, o setor é definido pelo **CNAE fiscal da sede**, que pode representar a atividade principal do grupo ou funções administrativas, podendo diferir da atividade produtiva exercida pelas filiais."""
            
            elif branch_mode == 'Somente Filiais':
                tooltip_sector = """**Setor Dominante (Atividade Produtiva)**

Indica a Divisão Industrial (CNAE – 2 dígitos) com maior número de unidades operacionais ativas.

Este modo reflete o **chão de fábrica**, mostrando onde a produção, transformação ou extração industrial está efetivamente concentrada."""
            
            else: # Todos
                tooltip_sector = """**Setor Dominante (Presença Industrial Total)**

Indica a Divisão Industrial (CNAE – 2 dígitos) com o maior número de estabelecimentos ativos, considerando matrizes e filiais.

Este modo reflete a **presença industrial total** no território analisado, medindo onde a atividade produtiva está mais distribuída fisicamente."""

            # Dynamic Tooltip Logic for Capital KPI
            if branch_mode == 'Somente Matrizes':
                tooltip_capital = """**Capital Social Médio (Somente Matrizes)**

Calcula a média exclusivamente entre empresas-matriz.

Este indicador expressa o porte econômico médio dos grupos presentes no recorte analisado, garantindo zero duplicidade."""
            
            elif branch_mode == 'Somente Filiais':
                tooltip_capital = """**Capital Social Médio (Reflexo do Grupo)**

Reflete o capital social do grupo empresarial ao qual as filiais pertencem, uma vez que o valor é replicado cadastralmente nas filiais.

**Atenção:** Não representa capital investido na filial, mas sim o porte da Holding controladora."""
            
            else: # Todos
                tooltip_capital = """**Capital Social Médio (Ajustado)**

Considera o capital das matrizes, evitando duplicidade de valores nas filiais.
O cálculo ignora repetições para entregar a média real de "Solidez Corporativa" do universo filtrado.

Representa a média do capital social declarado das empresas ativas, conforme dados oficials."""

            # Dynamic Tooltip Logic for Count KPI
            if branch_mode == 'Somente Matrizes':
                tooltip_count = """**Amostra Analisada (Somente Matrizes)**

Representa a quantidade total de CNPJs ativos que atendem a todos os filtros.

**Modo Atual:** Considera apenas empresas-sede (CNPJ base).

Este indicador mede a quantidade de grupos econômicos únicos no recorte analisado."""
            
            elif branch_mode == 'Somente Filiais':
                tooltip_count = """**Amostra Analisada (Somente Filiais)**

Representa a quantidade total de CNPJs ativos que atendem a todos os filtros.

**Modo Atual:** Considera apenas unidades operacionais.

Este indicador mede volume de presença empresarial no recorte analisado."""

            else: # Todos
                tooltip_count = """**Amostra Analisada (Total)**

Representa a quantidade total de CNPJs ativos que atendem a todos os filtros.

**Modo Atual:** Contagem estabelecimento por estabelecimento (inclui matrizes e filiais).

Este indicador mede volume de presença empresarial no recorte analisado e não representa quantidade de empresas únicas."""

            k1.metric(
                "Amostra Analisada", 
                fmt_total, 
                "Empresas",
                help=tooltip_count
            )
            k2.metric(
                "Capital Social Médio", 
                fmt_cap_display, 
                "Média Global",
                help=tooltip_capital
            )
            k3.metric(
                "Setor Dominante", 
                leader_name, 
                "Maior Volume",
                help=tooltip_sector
            )
            k4.metric(
                "Concentração (Top 1)", 
                f"{concentration:.1f}%".replace(".", ","), 
                "Share do Líder",
                help="Porcentagem da base total representada pelo setor dominante."
            )

            st.divider()

            # 3. Market Leaders (Ranking)
            # Storytelling: After seeing the "Total Market", the next question is "Who are they?".
            st.markdown("### Liderança de Mercado (Top 100)")
            st.caption("Quem manda no mercado filtrado? (Ranking por Capital Social - Matrizes)")
            
            # Filters for Ranking (Strictly Matriz & Limit 100)
            filters_rank = mi_filters.copy()
            filters_rank['branch_mode'] = 'Somente Matrizes'
            
            # Optimization: Check if we can reuse an existing aggregation? No, we need names.
            with st.spinner("Identificando líderes..."):
                df_top100 = db.get_filtered_companies(limit=100, **filters_rank)
            
            if not df_top100.empty:
                 # Format logic
                 df_top100 = df_top100.sort_values('capital_social', ascending=False).reset_index(drop=True)
                 
                 # Prepare Display Columns
                 if 'capital_social' in df_top100.columns:
                      # BR Format: R$ 1.500.000,00
                      df_top100['Capital_Fmt_BR'] = df_top100['capital_social'].apply(
                          lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                      )
                 
                 # Ensure CNAE is available (fallback if not present)
                 if 'cnae_desc' not in df_top100.columns and 'cnae_fiscal_principal' in df_top100.columns:
                     df_top100['cnae_info'] = df_top100['cnae_fiscal_principal']
                 elif 'cnae_desc' in df_top100.columns:
                     df_top100['cnae_info'] = df_top100['cnae_desc']
                 else:
                     df_top100['cnae_info'] = "-"

                 # Global CNPJ Format
                 if 'cnpj_ordem' in df_top100.columns and 'cnpj_dv' in df_top100.columns:
                      df_top100['cnpj_basico'] = df_top100['cnpj_basico'].astype(str).str.zfill(8)
                      df_top100['cnpj_ordem'] = df_top100['cnpj_ordem'].astype(str).str.zfill(4)
                      df_top100['cnpj_dv'] = df_top100['cnpj_dv'].astype(str).str.zfill(2)
                      df_top100['cnpj_real'] = (
                          df_top100['cnpj_basico'].str[:2] + "." + 
                          df_top100['cnpj_basico'].str[2:5] + "." + 
                          df_top100['cnpj_basico'].str[5:] + "/" + 
                          df_top100['cnpj_ordem'] + "-" + 
                          df_top100['cnpj_dv']
                      )
                 else:
                      df_top100['cnpj_real'] = df_top100['cnpj_basico']

                 df_top100['#'] = df_top100.index + 1
                 
                 # --- MODERN UI: Podium ---
                 st.markdown("##### Os 3 Gigantes")
                 m1, m2, m3 = st.columns(3)
                 
                 def safe_metric(idx, exact_col):
                     if len(df_top100) > idx:
                         row = df_top100.iloc[idx]
                         val = row['capital_social']
                         fmt_val = f"R$ {val/1e9:,.1f} B" if val > 1e9 else f"R$ {val/1e6:,.1f} M"
                         exact_col.metric(
                            f"#{idx+1} {row['razao_social'][:20]}...", 
                            fmt_val, 
                            "Capital Social",
                            help=f"Razão Social Completa: {row['razao_social']}\nCNPJ: {row['cnpj_basico']}\nCapital Declarado: R$ {val:,.2f}"
                         )
                 
                 safe_metric(0, m1)
                 safe_metric(1, m2)
                 safe_metric(2, m3)
                 
                 # --- MODERN UI: Chart ---
                 st.markdown("##### Comparativo (Top 10)")
                 chart_rank = alt.Chart(df_top100.head(10)).mark_bar().encode(
                     x=alt.X('capital_social:Q', title='Capital Social (R$)', axis=alt.Axis(format=',.2s')), # SI Strings
                     y=alt.Y('razao_social:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300)),
                     color=alt.value('#f1c40f'), # Gold color
                     tooltip=[
                         alt.Tooltip('razao_social', title='Empresa'), 
                         alt.Tooltip('Capital_Fmt_BR', title='Capital Social'), 
                         alt.Tooltip('uf', title='UF'),
                         alt.Tooltip('cnae_info', title='Atividade Principal')
                     ]
                 ).properties(height=350)
                 st.altair_chart(chart_rank, use_container_width=True)

                 # --- MODERN UI: Full List (Hidden) ---
                 with st.expander("Ver Lista Completa (Top 100)"):
                     st.dataframe(
                        df_top100,
                        height=400,
                        use_container_width=True,
                        column_order=["#", "cnpj_real", "razao_social", "Capital_Fmt", "uf", "municipio"],
                        column_config={
                            "#": st.column_config.NumberColumn("#", width="small"),
                            "cnpj_real": st.column_config.TextColumn("CNPJ", width="medium"),
                            "razao_social": st.column_config.TextColumn("Razão Social", width="large"),
                            "Capital_Fmt": st.column_config.TextColumn("Capital Social"),
                            "uf": "UF",
                            "municipio": "Cidade"
                        },
                        hide_index=True
                     )
            else:
                st.info("Não há dados suficientes para gerar o ranking.")

            st.markdown("---")

            # 4. Contexto Industrial (Report Layout)
            st.markdown("### Análise Industrial")
            
            # Row 1: Setorial (Full Width)
            st.markdown("#### Distribuição Setorial")
            st.caption("Volume de empresas por atividade principal (CNAE).")
            if not df_sectors.empty:
                    # Enrich Labels
                    df_divs = get_options_cached(db, 'get_industrial_divisions')
                    if not df_divs.empty:
                        df_sectors = df_sectors.merge(df_divs, left_on='sector_code', right_on='division_code', how='left')
                        df_sectors['label'] = df_sectors['label'].fillna(df_sectors['sector_code'])
                    else:
                        df_sectors['label'] = df_sectors['sector_code']
                
                    chart_sec = alt.Chart(df_sectors.head(15)).mark_bar().encode(
                        x=alt.X('count:Q', title='Quantidade'),
                        y=alt.Y('label:N', sort='-x', title=None),
                        color=alt.Color('count:Q', legend=None),
                        tooltip=['sector_code', 'label', 'count']
                    ).properties(height=400)
                    st.altair_chart(chart_sec, use_container_width=True)
            else:
                st.info("Sem dados setoriais.")

            # Row 2: Geographic Comparison (Side by Side)
            c_hub, c_pol = st.columns(2)
            
            with c_hub:
                st.markdown("#### Hubs Regionais (Top 10 Estados)")
                st.caption("Distribuição por UF.")
                df_states = db.get_geo_distribution(**mi_filters)
                if not df_states.empty:
                    chart_states = alt.Chart(df_states.head(10)).mark_bar().encode(
                        x=alt.X('count:Q', title='Quantidade'),
                        y=alt.Y('uf:N', sort='-x', title='Estado'),
                        color=alt.value('#3182bd'),
                        tooltip=['uf', 'count']
                    ).properties(height=400)
                    st.altair_chart(chart_states, use_container_width=True)
                else:
                    st.info("Sem dados regionais.")

            with c_pol:
                st.markdown("#### Pólos Locais (Top 10 Cidades)")
                st.caption("Municípios com maior concentração.")
                df_cities = db.get_city_distribution(**mi_filters)
                if not df_cities.empty:
                    chart_cities = alt.Chart(df_cities.head(10)).mark_bar().encode(
                        x=alt.X('count:Q', title='Quantidade'),
                        y=alt.Y('city:N', sort='-x', title=None),
                        color=alt.value('#2ca02c'), # Greenish
                        tooltip=[
                            alt.Tooltip('city', title='Município'),
                            alt.Tooltip('count', title='Qtd', format=',d')
                        ]
                    ).properties(height=400)
                    st.altair_chart(chart_cities, use_container_width=True)
                else:
                    st.info("Sem dados municipais.")

            st.divider()    

            # 5. Detailed Asset List (Unified View - No Rank)
            st.markdown("### Screen de Ativos (Geral)")
            st.caption("Listagem completa (Matrizes e Filiais aglutinadas).")
            
            df_disp = df_companies.copy()
            
            # Enrich Data using Utils
            # 1. Porte
            porte_map = {'00': 'N/D', '01': 'Micro', '03': 'Pequeno', '05': 'Médio/Gd'}
            if 'porte_empresa' in df_disp.columns:
                df_disp['Porte'] = df_disp['porte_empresa'].fillna('00').apply(lambda x: porte_map.get(str(x), str(x)))
            
            # 2. Status
            if 'situacao_cadastral' in df_disp.columns:
                df_disp['Status'] = df_disp['situacao_cadastral'].apply(get_status_description)
            else:
                df_disp['Status'] = "-"
            
            # 3. Date
            if 'data_inicio_atividade' in df_disp.columns:
                df_disp['Início'] = df_disp['data_inicio_atividade'].astype(str).apply(format_date)
            else:
                df_disp['Início'] = "-"

            # 4. Descriptions (Ensure columns exist from previous merges)
            # Database now likely returns these, so we check before overwriting/creating
            if 'cnae_desc' not in df_disp.columns: 
                df_disp['cnae_desc'] = df_disp.get('cnae_fiscal_principal', '-')
                
            # 'natureza_desc' is now returned by DB, safe check to avoid duplication if logic changes
            if 'natureza_desc' not in df_disp.columns: 
                df_disp['natureza_desc'] = df_disp.get('natureza_juridica', '-')
            
            # Select Columns
            # cols = ['cnpj_basico', 'razao_social', 'uf', 'municipio', 'capital_social', 'Porte']
            
            # Format Capital for BR Display (String)
            df_disp['Capital (R$)'] = df_disp['capital_social'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

            # Enrich with Type Label (Visual Distinction)
            if 'identificador_matriz_filial' in df_disp.columns:
                df_disp['tipo_label'] = df_disp['identificador_matriz_filial'].map({
                    '1': '🏢 MATRIZ',
                    '2': '🏭 FILIAL'
                }).fillna('❓')
            else:
                 df_disp['tipo_label'] = '-'

            # Sort & Show
            # 1. Sort by Capital (Big Groups First)
            # 2. Then by Root CNPJ (To keep branches together if Capital is identical)
            # 3. Then by Type (1=Matriz must come before 2=Filial)
            df_show = df_disp.sort_values(
                by=['capital_social', 'cnpj_basico', 'identificador_matriz_filial'], 
                ascending=[False, True, True] 
            ).reset_index(drop=True)
            
            # NO RANKING here, just the list
            
            st.dataframe(
                df_show,
                height=600,
                use_container_width=True,
                column_order=["cnpj_real", "tipo_label", "razao_social", "Capital (R$)", "uf", "municipio", "Porte", "Status", "Início", "cnae_desc", "natureza_desc"],
                column_config={
                    "cnpj_real": st.column_config.TextColumn("CNPJ", width="medium"),
                    "tipo_label": st.column_config.TextColumn("Tipo", width="small"),
                    "razao_social": st.column_config.TextColumn("Razão Social", width="large"),
                    "Capital (R$)": st.column_config.TextColumn("Capital Social"),
                    "uf": "UF",
                    "municipio": "Cidade",
                    "Porte": "Porte",
                    "Início": "Data Abertura",
                    "cnae_desc": st.column_config.TextColumn("Atividade Principal (CNAE)", width="medium"),
                    "natureza_desc": st.column_config.TextColumn("Natureza Jurídica", width="medium")
                },
                hide_index=True
            )


                

        except Exception as e:
            st.error(f"Erro na análise de mercado: {e}")
