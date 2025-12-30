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

# --- LOCAL PAGE FILTERS (Top of Page) ---

def _render_common_geo_activity(db: CNPJDatabase, key_suffix: str):
    """Helper to render Geo/Activity filters common to all pages."""
    c1, c2, c3 = st.columns([1, 1, 2])
    
    with c1:
        states = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
        sel_ufs = st.multiselect("Estados", states, key=f"ufs_{key_suffix}")
    
    with c2:
        df_muni = get_options_cached(db, 'get_all_municipios')
        sel_city_codes = []
        if not df_muni.empty:
            if sel_ufs:
                muni_opts = df_muni[df_muni['uf'].isin(sel_ufs)]['descricao'].tolist() if 'uf' in df_muni.columns else df_muni['descricao'].tolist()
            else:
                muni_opts = df_muni['descricao'].tolist()  
            sel_city_names = st.multiselect("Municípios", muni_opts, placeholder="Todas", key=f"city_{key_suffix}")
            if sel_city_names:
                sel_city_codes = df_muni[df_muni['descricao'].isin(sel_city_names)]['codigo'].tolist()
    
    with c3:
        df_sectors = get_options_cached(db, 'get_industrial_divisions')
        sel_sectors = []
        if not df_sectors.empty:
            sec_opts = df_sectors['label'].tolist()
            ui_sectors = st.multiselect("Setores (CNAE)", sec_opts, placeholder="Todos os Setores", key=f"sec_{key_suffix}")
            sel_sectors = [s.split(" - ")[0] for s in ui_sectors]

    return sel_ufs, sel_city_codes, sel_sectors

def render_structure_filters(db: CNPJDatabase) -> dict:
    """Filters for 'Estrutura de Mercado' (Full Company Details)."""
    with st.expander("Filtros & Segmentação", expanded=False):
        # 0. Search (Restored from Global)
        c_search, c_empty = st.columns([3, 1])
        with c_search:
            search_query = st.text_input("Busca Rápida (Nome ou CNPJ)", placeholder="Ex: PETROBRAS ou 33.000.167...", key='search_struct')
        
        st.divider()

        # 1. Global
        sel_ufs, sel_city_codes, sel_sectors = _render_common_geo_activity(db, "struct")
        
        st.divider()
        
        # 2. Detailed
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_portes_ui = st.multiselect("Porte", ["01 (ME)", "03 (EPP)", "05 (Demais)"], default=["05 (Demais)"], key='f_porte_struct')
            sel_portes = [p.split()[0] for p in sel_portes_ui] if sel_portes_ui else []
            
        with c2:
            sel_branch_mode = st.radio("Escopo", ["Todos", "Somente Matrizes", "Somente Filiais"], index=0, horizontal=True, key='f_scope_struct')
            
        with c3:
            d_range = st.date_input("Data Abertura", [], key='f_date_struct')
            d_start = d_range[0].strftime("%Y%m%d") if len(d_range) == 2 else None
            d_end = d_range[1].strftime("%Y%m%d") if len(d_range) == 2 else None

        # 3. Capital
        c_cap1, c_cap2 = st.columns(2)
        min_cap = c_cap1.number_input("Capital Mín.", 0.0, step=100000.0, format="%.0f", key='f_min_cap_struct')
        max_cap = c_cap2.number_input("Capital Máx.", 0.0, step=100000.0, format="%.0f", key='f_max_cap_struct')

    return {
        "ufs": sel_ufs, "municipio_codes": sel_city_codes, "sectors": sel_sectors,
        "portes": sel_portes, "branch_mode": sel_branch_mode,
        "min_capital": min_cap, "max_capital": max_cap if max_cap > 0 else None,
        "date_start": d_start, "date_end": d_end, "limit": 1000, "only_active": True,
        "search_term": search_query.strip() if search_query else None
    }

def render_macro_filters(db: CNPJDatabase) -> dict:
    """Filters for 'Atividade Macro' (Focus on Geo/Sector)."""
    with st.expander("Filtros Regionais e Setoriais", expanded=False):
        sel_ufs, sel_city_codes, sel_sectors = _render_common_geo_activity(db, "macro")
        
    return {
        "ufs": sel_ufs, "municipio_codes": sel_city_codes, "sectors": sel_sectors,
        "portes": ["05"], "branch_mode": "Todos", "limit": 1000, "only_active": True,
        "min_capital": 0.0, "max_capital": None, "date_start": None, "date_end": None
    }

def render_strategy_filters(db: CNPJDatabase) -> dict:
    """Filters for 'Dinâmica Estratégica' (Micro correlation)."""
    with st.expander("Filtros de Correlação (Micro)", expanded=False):
        sel_ufs, sel_city_codes, sel_sectors = _render_common_geo_activity(db, "strat")
        st.caption("Filtre o segmento Micro para correlacionar com a Produção Industrial Nacional.")
        
    return {
        "ufs": sel_ufs, "municipio_codes": sel_city_codes, "sectors": sel_sectors,
        "portes": ["05"], "branch_mode": "Todos", "limit": 1000, "only_active": True,
        "min_capital": 0.0, "max_capital": None, "date_start": None, "date_end": None
    }

def render_strategic_view(db: CNPJDatabase, filters):
    st.subheader("Dinâmica Industrial (Micro + Macro)")
    st.markdown("""
    **Como Evolui?**
    Aqui cruzamos a **Estrutura** (Novas Empresas) com a **Atividade** (Produção IBGE) para entender o ciclo econômico.
    *Objetivo: Identificar correlações entre investimento empresarial e produção real.*
    """)
    
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
                if corr > 0.7: insight = "Forte Correlação Positiva"
                elif corr < -0.7: insight = "Forte Correlação Negativa"
                elif abs(corr) < 0.3: insight = "Sem Correlação Clara"
                else: insight = "Correlação Moderada"
                
                # --- KPI CARD FOR CORRELATION ---
                st.markdown("##### Sincronia de Mercado")
                
                c_kpi, c_desc = st.columns([1, 2])
                c_kpi.metric("Correlação de Pearson", f"{corr:.2f}", insight)
                
                with c_desc:
                    st.markdown("""
                    <div style="background-color: var(--secondary-background-color); padding: 15px; border-radius: 8px; border: 1px solid rgba(128, 128, 128, 0.2);">
                        <span style="font-weight: 600; font-size: 0.9em; opacity: 0.8;">O que isso significa?</span><br>
                        <span style="font-size: 0.85em; opacity: 0.7;">
                            O coeficiente mede se a <b>abertura de empresas</b> segue o ritmo da <b>produção industrial</b>.
                            Valores próximos de <b>1.0</b> indicam que fábricas abrem exatamente quando a produção sobe.
                        </span>
                    </div>
                    """, unsafe_allow_html=True)

                st.divider()

                # --- DUAL AXIS CHART ---
                st.markdown("### Cruzamento de Tendências")
                st.caption("Comparativo entre a abertura de empresas (no seu filtro) e a Produção Industrial Nacional.")
                
                base = alt.Chart(df_chart).encode(x=alt.X('date:T', axis=alt.Axis(format='%Y'), title=None))
                
                line_micro = base.mark_line(color='#ff7f0e', strokeWidth=3).encode(
                    y=alt.Y('Novas Empresas', axis=alt.Axis(title='Novas Empresas', titleColor='#ff7f0e'))
                )
                
                line_macro = base.mark_line(color='#1f77b4', strokeDash=[5,5], strokeWidth=3).encode(
                    y=alt.Y('Indústria (IBGE)', axis=alt.Axis(title='Benchmark Nacional (IBGE)', titleColor='#1f77b4'))
                )
                
                combined = (line_micro + line_macro).resolve_scale(y='independent').encode(
                    tooltip=[
                        alt.Tooltip('date:T', title='Data', format='%b/%Y'),
                        alt.Tooltip('Novas Empresas', title='Novas Empresas', format=',d'),
                        alt.Tooltip('Indústria (IBGE)', title='Indústria (idx)', format='.2f')
                    ]
                ).properties(height=400)
                
                st.altair_chart(combined, use_container_width=True)
                
                st.info("💡 **Dica de Leitura:** A linha **Laranja (Sua Seleção)** mostra o ímpeto empreendedor. A linha **Azul (Tracejada)** é o ritmo do Brasil. Se a laranja sobe antes, é antecipação de ciclo.")
                
                with st.expander("Insight Avançado: O efeito 'Time Lag'", expanded=False):
                     st.write("""
                     **Atenção:** Frequentemente existe uma defasagem (atraso) entre a abertura da empresa (linha laranja) e o início da produção (linha azul).
                     *   Fábricas demoram para ser construídas.
                     *   Se a linha laranja sobe hoje e a azul não, pode indicar **aumento de capacidade futura** (investimento em andamento).
                     """)

        if not has_correlation:
            # FALLBACK VIEW
            if not df_trend.empty:
                st.markdown("##### Tendência de Abertura Identificada")
                
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
    with st.expander("Guia de Leitura: Entenda os Indicadores (SIDRA/IBGE)", expanded=False):
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
            
            # Keys for legacy chart support
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
            
            # 2. Get Metrics for SELECTED Date (Manually)
            metrics = {}
            if selected_date and not loc_df.empty:
                current_data = loc_df[loc_df['date'] == selected_date]
                for _, row in current_data.iterrows():
                    metrics[row['variable']] = row['value']
            
            if selected_date:
                # Prominent Reference Date Display
                ref_date_str = selected_date.strftime('%m/%Y')
                is_latest = (selected_date == available_dates[0])
                note = "(Dados mais recentes)" if is_latest else "(Histórico selecionado)"
                
                st.markdown(f"""
                <div style="background-color: var(--secondary-background-color); padding: 12px; border-radius: 8px; margin-bottom: 24px; border-left: 4px solid var(--primary-color); box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    <span style="font-size: 0.9em; font-weight: 600; opacity: 0.8;">Mês de Referência (IBGE):</span>
                    <span style="font-size: 1.1em; font-weight: 700; margin-left: 8px;">{ref_date_str}</span>
                    <span style="font-size: 0.85em; opacity: 0.7; margin-left: 10px;">{note} • {actual_loc}</span>
                </div>
                """, unsafe_allow_html=True)
            
            # --- SECTION 1: KPIS (Standardized Grid) ---
            st.markdown("##### Indicadores Chave")
            
            # Row 1: Structural & Seasonal
            c1, c2, c3 = st.columns(3)
            c1.metric("Índice (Base Fixa)", f"{metrics.get(k_idx_clean, 0):.2f}", "Base: 2022 = 100")
            c2.metric("Índice (Sazonal)", f"{metrics.get(k_idx_saz, 0):.2f}", "Ajustado")
            c3.metric("Var. Mensal (Sazonal)", f"{metrics.get(k_mom_saz, 0):.2f}%", "Ritmo (Mês/Mês)")
            
            # Row 2: Variações de Longo Prazo
            # Small spacer
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            
            c4, c5, c6 = st.columns(3)
            c4.metric("Var. Mensal (YoY)", f"{metrics.get(k_mom_yoy, 0):.2f}%", "Out/25 vs Out/24")
            c5.metric("Acumulado no Ano", f"{metrics.get(k_acc_year, 0):.2f}%", "Jan até Atual")
            c6.metric("Acumulado 12 Meses", f"{metrics.get(k_acc_12m, 0):.2f}%", "Tendência (Longo Prazo)")
            
            st.markdown("---")
            
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

            st.markdown("---")
            
            # --- SECTION 2: CHARTS (Grid Layout) ---
            c_title, c_f = st.columns([3, 1])
            with c_title:
                st.markdown("### Análise de Tendências")
                st.caption("Monitoramento do ritmo de atividade e comparação entre períodos.")
            
            with c_f:
                # Timeframe Filter Logic
                available_years = sorted(loc_df['date'].dt.year.unique(), reverse=True)
                year_options = ["Últimos 24 Meses", "Todo o Histórico"] + [str(y) for y in available_years]
                
                chart_timeframe = st.selectbox("Recorte Temporal", year_options, index=0)
            
            # Filter Data Helper
            def filter_by_timeframe(df_in):
                if chart_timeframe == "Todo o Histórico":
                    return df_in
                elif chart_timeframe == "Últimos 24 Meses":
                    cutoff = pd.Timestamp.now() - pd.DateOffset(months=24)
                    return df_in[df_in['date'] >= cutoff]
                else:
                    # Specific Year
                    try:
                        sel_year = int(chart_timeframe)
                        return df_in[df_in['date'].dt.year == sel_year]
                    except:
                        return df_in # Fallback

            # Row 1: Pulse vs Trend
            c_pulse, c_trend = st.columns(2)
            
            with c_pulse:
                st.markdown("#### O Ritmo (Curto Prazo)")
                st.caption("Variação Mensal (Sazonal) - O termômetro da volatilidade.")
                
                df_pulse = df_ibge[ (df_ibge['variable'] == mom_key) & (df_ibge['location'] == actual_loc) ]
                df_pulse = filter_by_timeframe(df_pulse)
                
                bar_pulse = alt.Chart(df_pulse).mark_bar().encode(
                    x=alt.X('date:T', axis=alt.Axis(format='%b/%y', labelAngle=-45), title=None),
                    y=alt.Y('value:Q', title='%'),
                    color=alt.condition(alt.datum.value > 0, alt.value('#2ca02c'), alt.value('#d62728')),

                    tooltip=[alt.Tooltip('date:T', format='%b/%Y'), alt.Tooltip('value', format='.2f')]
                ).properties(height=280)
                st.altair_chart(bar_pulse, use_container_width=True)
                
            with c_trend:
                st.markdown("#### A Tendência (Longo Prazo)")
                st.caption("Acumulado 12 Meses - Direção estrutural do ciclo.")
                
                df_trend = df_ibge[ (df_ibge['variable'] == acc12_key) & (df_ibge['location'] == actual_loc) ]
                df_trend = filter_by_timeframe(df_trend)
                
                area_trend = alt.Chart(df_trend).mark_area(line={'color':'#1f77b4'}, color=alt.Gradient(
                    gradient='linear', stops=[alt.GradientStop(color='white', offset=0), alt.GradientStop(color='#1f77b4', offset=1)],
                    x1=1, x2=1, y1=1, y2=0
                ), opacity=0.5).encode(
                    x=alt.X('date:T', axis=alt.Axis(format='%b/%y', labelAngle=-45), title=None),
                    y=alt.Y('value:Q', title='%'),

                    tooltip=[alt.Tooltip('date:T', format='%b/%Y'), alt.Tooltip('value', format='.2f')]
                ).properties(height=280)
                st.altair_chart(area_trend, use_container_width=True)

            # Row 2: Annual Performance
            st.divider()
            
            c_yoy, c_year = st.columns(2)
            
            with c_yoy:
                st.markdown("#### Comparativo Anual (YoY)")
                st.caption("Variação vs Mesmo Mês Ano Anterior")
                
                df_yoy = df_ibge[ (df_ibge['variable'] == k_mom_yoy) & (df_ibge['location'] == actual_loc) ]
                df_yoy = filter_by_timeframe(df_yoy)
                
                bar_yoy = alt.Chart(df_yoy).mark_bar().encode(
                    x=alt.X('date:T', axis=alt.Axis(format='%b/%y', labelAngle=-45), title=None),
                    y=alt.Y('value:Q', title='%'),
                    color=alt.condition(alt.datum.value > 0, alt.value('#2ca02c'), alt.value('#d62728')),
                    tooltip=[alt.Tooltip('date:T', format='%b/%Y'), alt.Tooltip('value', format='.2f')]
                ).properties(height=250)
                st.altair_chart(bar_yoy, use_container_width=True)

            with c_year:
                st.markdown("#### Acumulado no Ano")
                st.caption("Desempenho no ano calendário corrente.")
                
                df_year = df_ibge[ (df_ibge['variable'] == k_acc_year) & (df_ibge['location'] == actual_loc) ]
                df_year = filter_by_timeframe(df_year)
                
                line_year = alt.Chart(df_year).mark_line(color='#9467bd', strokeWidth=3).encode(
                    x=alt.X('date:T', axis=alt.Axis(format='%b/%y', labelAngle=-45), title=None),
                    y=alt.Y('value:Q', title='%'),
                    tooltip=[alt.Tooltip('date:T', format='%b/%Y'), alt.Tooltip('value', format='.2f')]
                ).properties(height=250)
                st.altair_chart(line_year, use_container_width=True)

            st.divider()

            # --- SECTION 3: STRUCTURAL DIAGNOSIS ---
            st.markdown(f"#### Nível da Atividade - {actual_loc}")
            st.caption("Índice de Base Fixa (2022=100) - Mostra o volume físico real produzido.")

            valid_locs = [actual_loc]
            if actual_loc != "Brasil":
                show_benchmark = st.checkbox("Comparar com Benchmark Nacional", value=False)
                if show_benchmark: valid_locs.append("Brasil")
            
            df_chart = df_ibge[ (df_ibge['variable'] == idx_key) & (df_ibge['location'].isin(valid_locs)) ].copy()
            df_chart = filter_by_timeframe(df_chart)
            
            base_chart = alt.Chart(df_chart).mark_line(point=True)
            if len(valid_locs) > 1:
                chart_ibge = base_chart.encode(
                    x=alt.X('date:T', title='Data', axis=alt.Axis(format='%b/%y', labelAngle=-45)),
                    y=alt.Y('value:Q', title='Índice (2022=100)', scale=alt.Scale(zero=False)),
                    color=alt.value('#FF8C00'),
                    strokeDash=alt.StrokeDash('location', title='Local', legend=alt.Legend(orient='bottom')),
                    tooltip=[alt.Tooltip('date:T', format='%b/%Y'), alt.Tooltip('value', format='.2f'), alt.Tooltip('location')]
                )
            else:
                chart_ibge = base_chart.encode(
                    x=alt.X('date:T', title='Data', axis=alt.Axis(format='%b/%y', labelAngle=-45)),
                    y=alt.Y('value:Q', title='Índice (2022=100)', scale=alt.Scale(zero=False)),
                    tooltip=[alt.Tooltip('date:T', format='%b/%Y'), alt.Tooltip('value', format='.2f')]
                )

            chart_ibge = chart_ibge.properties(height=400).interactive()
            st.altair_chart(chart_ibge, use_container_width=True)

            # --- PRO LEVEL: SCATTER & RANKING ---
            st.markdown("---")
            st.subheader("Diagnóstico Estrutural (Visão Panorâmica)")
            st.markdown("Onde sua seleção se encaixa no cenário nacional? Compare com outros estados/setores.")
            
            latest_date_all = df_ibge['date'].max()
            df_snapshot = df_ibge[df_ibge['date'] == latest_date_all].copy()
            
            if not df_snapshot.empty:
                df_pivot = df_snapshot.pivot(index='location', columns='variable', values='value').reset_index()
                
                if mom_key in df_pivot.columns and acc12_key in df_pivot.columns:
                    c_scat, c_rank = st.columns([3, 2])
                    
                    with c_scat:
                        st.markdown("#### Mapa de Ciclo Econômico")
                        st.caption(f"Posicionamento dos Estados/Regiões em {latest_date_all.strftime('%m/%Y')}")
                        
                        base_scat = alt.Chart(df_pivot).mark_circle(size=150, opacity=0.9).encode(
                            x=alt.X(acc12_key, title='Tendência (Acum. 12m %)', axis=alt.Axis(grid=False)),
                            y=alt.Y(mom_key, title='Ritmo (Var. Mensal %)', axis=alt.Axis(grid=False)),
                            color=alt.condition(alt.datum.location == actual_loc, alt.value('#d62728'), alt.value('#cbd5e1')),
                            tooltip=[alt.Tooltip('location'), alt.Tooltip(acc12_key, format='.2f'), alt.Tooltip(mom_key, format='.2f')]
                        ).properties(height=400)
                        
                        text_scat = base_scat.mark_text(align='left', dx=10, fontSize=11, fontWeight=600).encode(text='location', color=alt.value('#334155'))
                        
                        rule_x = alt.Chart(pd.DataFrame({'x': [0]})).mark_rule(color='#94a3b8', strokeDash=[5,5]).encode(x='x')
                        rule_y = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(color='#94a3b8', strokeDash=[5,5]).encode(y='y')
                        
                        st.altair_chart((base_scat + text_scat + rule_x + rule_y).interactive(), use_container_width=True)
                        
                    with c_rank:
                        st.markdown("#### Ranking de Desempenho (12m)")
                        st.caption("Quem está crescendo mais?")
                        
                        rank_chart = alt.Chart(df_pivot).mark_bar().encode(
                            x=alt.X(acc12_key, title='%', axis=alt.Axis(grid=False)),
                            y=alt.Y('location', sort='-x', title=None),
                            color=alt.condition(alt.datum.location == actual_loc, alt.value('#d62728'), alt.value('#3b82f6')),
                            tooltip=[alt.Tooltip('location'), alt.Tooltip(acc12_key, format='.2f')]
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
    
    #### Estrutura Técnica do CNPJ
    Cada registro possui 14 dígitos organizados no formato `AA.AAA.AAA/BBBB-CC`:
    
    *   `AA.AAA.AAA` → **CNPJ Raiz (`cnpj_basico`)**: Identifica a empresa.
    *   `BBBB` → **Ordem (`cnpj_ordem`)**: Identifica o estabelecimento.
        *   `0001` → Geralmente a **Matriz**.
        *   `0002`, `0003`... → **Filiais**.
    *   `CC` → **Dígito Verificador (`cnpj_dv`)**.

    #### Como identificamos no Banco de Dados?
    Utilizamos o campo oficial `identificador_matriz_filial`:
    *   Valor `1` → **Matriz** (Sede administrativa/jurídica).
    *   Valor `2` → **Filial** (Unidade operacional, fábrica, cd, etc).

    > **Atenção (Caso Especial/Fusões):**
    > Nem toda Matriz é `/0001`. Em casos de fusão, aquisição ou reestruturação (como no caso da Lactalis), a sede pode assumir outro número (ex: `/0054`).
    > **O que vale para o dashboard é o campo "Tipo" (Status 1), não o número do sufixo.**

    ---

    #### As Três "Lentes" do Dashboard:

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
    | Crescendo | Crescendo | **Expansão Real:** O mercado demanda mais, e as empresas estão investindo em nova capacidade para atender. |
    | Crescendo | Estável | **Uso de Capacidade:** A demanda subiu, mas a indústria está atendendo com as fábricas que já existem (aumento de turnos/ocupação). |
    | Caindo | Crescendo | **Aposta Futura (ou Defasagem):** A produção está ruim hoje, mas empresas estão abrindo filiais. Pode indicar *novos entrantes* ou *projetos de longo prazo* maturando. |
    | Caindo | Caindo | **Crise Estrutural:** Retração tanto na saída (vendas) quanto no investimento (fechamento de unidades). |

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
        background-color: var(--background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

    st.subheader("Estrutura de Mercado (Micro)")
    st.markdown("""
    **Quem são os Players?**
    Análise fundamentalista da base instalada (CNPJ). 
    *Foco: Market Share, Concentração Geográfica e Solidez Financeira.*
    """)
    
    with st.spinner("Processando Big Data..."):
        try:
            # 1. Prepare Data
            mi_filters = filters.copy()
            limit = mi_filters.pop('limit', 1000)
            
            # --- FETCH DATA ---
            metrics_view = db.get_aggregation_metrics(**mi_filters)
            true_total = metrics_view.get('count', 0)
            
            filters_fin = mi_filters.copy()
            filters_fin['branch_mode'] = 'Somente Matrizes'
            metrics_fin = db.get_aggregation_metrics(**filters_fin)
            true_avg_cap = metrics_fin.get('avg_cap', 0.0)
            
            df_sectors = db.get_sector_distribution(**mi_filters)
            df_companies = db.get_filtered_companies(limit=limit, **mi_filters)

            # --- ENRICHMENT ---
            if not df_companies.empty:
                 df_nat = get_options_cached(db, 'get_all_naturezas')
                 df_cnae = get_options_cached(db, 'get_all_cnaes')
                 df_muni = get_options_cached(db, 'get_all_municipios')

                 if 'natureza_desc' not in df_companies.columns and not df_nat.empty and 'natureza_juridica' in df_companies.columns:
                     df_companies = df_companies.merge(df_nat, left_on='natureza_juridica', right_on='codigo', how='left').rename(columns={'descricao': 'natureza_desc'})
                
                 if not df_companies.empty and 'cnae_fiscal_principal' in df_companies.columns and not df_cnae.empty:
                     df_companies = df_companies.merge(df_cnae, left_on='cnae_fiscal_principal', right_on='codigo', how='left').rename(columns={'descricao': 'cnae_desc'})

                 if 'municipio' not in df_companies.columns and not df_muni.empty and 'municipio_codigo' in df_companies.columns:
                     df_companies = df_companies.merge(df_muni, left_on='municipio_codigo', right_on='codigo', how='left').rename(columns={'descricao': 'municipio'})
            
            if df_companies.empty:
                st.warning("Nenhum player encontrado com os filtros atuais.")
                return

            # Format CNPJ
            if 'cnpj_ordem' in df_companies.columns and 'cnpj_dv' in df_companies.columns:
                 df_companies['cnpj_basico'] = df_companies['cnpj_basico'].astype(str).str.zfill(8)
                 df_companies['cnpj_ordem'] = df_companies['cnpj_ordem'].astype(str).str.zfill(4)
                 df_companies['cnpj_dv'] = df_companies['cnpj_dv'].astype(str).str.zfill(2)
                 df_companies['cnpj_real'] = df_companies['cnpj_basico'].str[:2] + "." + df_companies['cnpj_basico'].str[2:5] + "." + df_companies['cnpj_basico'].str[5:] + "/" + df_companies['cnpj_ordem'] + "-" + df_companies['cnpj_dv']
            else:
                 df_companies['cnpj_real'] = df_companies['cnpj_basico']

            # --- SECTION 1: KPIS (Top Row) ---
            # Helper: Concentration
            total_mkt = true_total if true_total > 0 else 1
            concentration = 0
            leader_name = "-"
            if not df_sectors.empty:
                top_sec = df_sectors.iloc[0]
                concentration = (top_sec['count'] / total_mkt) * 100
                leader_name = top_sec['sector_code']

            # Helper: Formats
            fmt_total = f"{true_total:,.0f}"
            if true_avg_cap >= 1e9: fmt_cap = f"R$ {true_avg_cap/1e9:,.2f} B"
            elif true_avg_cap >= 1e6: fmt_cap = f"R$ {true_avg_cap/1e6:,.2f} MM"
            else: fmt_cap = f"R$ {true_avg_cap:,.2f}"

            st.markdown("##### Indicadores Chave")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total de Players", fmt_total, "Empresas Ativas")
            k2.metric("Capital Médio", fmt_cap, "Solidez Financeira")
            k3.metric("Setor Líder", leader_name, "Maior Volume")
            k4.metric("Concentração", f"{concentration:.1f}%", "Share do Top 1")
            
            st.markdown("---")

            # --- SECTION 2: LEADERSHIP (Podium + Chart) ---
            st.markdown("##### Liderança de Mercado")
            
            # Fetch Top 100 for Ranking
            filters_rank = mi_filters.copy()
            filters_rank['branch_mode'] = 'Somente Matrizes'
            df_top100 = db.get_filtered_companies(limit=100, **filters_rank)
            
            if not df_top100.empty:
                 df_top100 = df_top100.sort_values('capital_social', ascending=False).reset_index(drop=True)
                 
                 c_podium, c_chart = st.columns([1, 2])
                 
                 with c_podium:
                     st.caption("**Top 3 Gigantes**")
                     for i in range(min(3, len(df_top100))):
                         row = df_top100.iloc[i]
                         val = row['capital_social']
                         val_fmt = f"R$ {val/1e9:,.1f} B" if val > 1e9 else f"R$ {val/1e6:,.1f} M"
                         st.markdown(f"""
                         <div style="background-color: var(--secondary-background-color); border-radius: 8px; padding: 10px; margin-bottom: 8px; border: 1px solid rgba(128, 128, 128, 0.2); border-left: 4px solid #f1c40f; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                            <div style="font-size: 0.8rem; font-weight: 600; opacity: 0.7;">#{i+1} LÍDER</div>
                            <div style="font-size: 0.95rem; font-weight: 700; word-wrap: break-word; white-space: normal;">{row['razao_social']}</div>
                            <div style="font-size: 0.8rem; opacity: 0.8;">{val_fmt}</div>
                         </div>
                         """, unsafe_allow_html=True)

                 with c_chart:
                     st.caption("**Ranking Top 10 (Capital Social)**")
                     chart_rank = alt.Chart(df_top100.head(10)).mark_bar().encode(
                         x=alt.X('capital_social:Q', title='Capital (R$)', axis=alt.Axis(format=',.2s', grid=False)),
                         y=alt.Y('razao_social:N', sort='-x', title=None, axis=alt.Axis(labelLimit=200)),
                         color=alt.value('#3b82f6'),
                         tooltip=['razao_social', 'capital_social']
                     ).properties(height=280)
                     st.altair_chart(chart_rank, use_container_width=True)
            else:
                st.info("Ranking indisponível para esta seleção.")

            st.markdown("---")

            # 4. Contexto Industrial (Análise Detalhada)
            st.markdown("### Análise Industrial Detalhada")
            st.markdown("Visão aprofundada da distribuição geográfica e setorial dos players.")

            # Row 1: Setorial (Full Width for Readability)
            st.markdown("#### Distribuição por Setor (Top 10)")
            st.caption("Volume de empresas por atividade principal (CNAE). Onde há maior concentração de negócios?")
            
            if not df_sectors.empty:
                # Enrich Labels
                df_divs = get_options_cached(db, 'get_industrial_divisions')
                if not df_divs.empty:
                    df_sectors = df_sectors.merge(df_divs, left_on='sector_code', right_on='division_code', how='left')
                    df_sectors['label'] = df_sectors['label'].fillna(df_sectors['sector_code'])
                else:
                    df_sectors['label'] = df_sectors['sector_code']
            
                chart_sec = alt.Chart(df_sectors.head(10)).mark_bar().encode(
                    x=alt.X('count:Q', title='Quantidade de Empresas', axis=alt.Axis(grid=True)),
                    y=alt.Y('label:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300)),
                    color=alt.Color('count:Q', legend=None, scale=alt.Scale(scheme='greens')),
                    tooltip=[
                        alt.Tooltip('sector_code', title='Cód'),
                        alt.Tooltip('label', title='Setor'),
                        alt.Tooltip('count', title='Volume', format=',d')
                    ]
                ).properties(height=400)
                st.altair_chart(chart_sec, use_container_width=True)
            else:
                st.info("Sem dados setoriais disponíveis.")

            st.divider()

            # Row 2: Geographic Comparison (Side by Side)
            c_hub, c_pol = st.columns(2)
            
            with c_hub:
                st.markdown("#### Hubs Estaduais (Top 10)")
                st.caption("Concentração por Unidade Federativa.")
                
                df_states = db.get_geo_distribution(**mi_filters)
                if not df_states.empty:
                    chart_states = alt.Chart(df_states.head(10)).mark_arc(outerRadius=120).encode(
                        theta=alt.Theta("count", stack=True),
                        color=alt.Color("uf", title="Estado"),
                        order=alt.Order("count", sort="descending"),
                        tooltip=["uf", alt.Tooltip("count", title="Empresas", format=",d")]
                    ).properties(height=350, title='Ranking Estadual')
                    st.altair_chart(chart_states, use_container_width=True)
                else:
                    st.info("Sem dados regionais.")

            with c_pol:
                st.markdown("#### Pólos Municipais (Top 10)")
                st.caption("Cidades com maior densidade empresarial.")
                
                df_cities = db.get_city_distribution(**mi_filters)
                if not df_cities.empty:
                    chart_cities = alt.Chart(df_cities.head(10)).mark_bar().encode(
                        x=alt.X('count:Q', title='Volume', axis=alt.Axis(format='d')),
                        y=alt.Y('city:N', sort='-x', title=None, axis=alt.Axis(labelLimit=150)),
                        color=alt.value('#2ca02c'), # Greenish
                        tooltip=[
                            alt.Tooltip('city', title='Município'),
                            alt.Tooltip('count', title='Empresas', format=',d')
                        ]
                    ).properties(height=350, title='Ranking Municipal')
                    st.altair_chart(chart_cities, use_container_width=True)
                else:
                    st.info("Sem dados municipais.")

            st.divider()

            # 4.5 Qualitative Profile (Maturity & Sophistication)
            st.markdown("### Perfil Qualitativo")
            st.caption("Análise da maturidade e sofisticação jurídica do mercado.")
            
            c_age, c_nature = st.columns(2)
            
            with c_age:
                st.markdown("#### Ciclo de Maturidade")
                st.caption("Distribuição por idade das empresas.")
                
                df_maturity = db.get_maturity_profile(**mi_filters)
                if not df_maturity.empty:
                    chart_maturity = alt.Chart(df_maturity).mark_bar().encode(
                        x=alt.X('count:Q', title='Quantidade', axis=alt.Axis(format='d')),
                        y=alt.Y('category:N', sort=None, title=None),
                        color=alt.Color('category:N', legend=None, scale=alt.Scale(
                            domain=['1. Novas Entrantes (< 3 anos)', '2. Jovens (3 a 9 anos)', '3. Consolidadas (10 a 20 anos)', '4. Veteranas (> 20 anos)'],
                            range=['#fee5d9', '#fcae91', '#fb6a4a', '#cb181d']
                        )),
                        tooltip=[
                            alt.Tooltip('category', title='Faixa Etária'),
                            alt.Tooltip('count', title='Empresas', format=',d')
                        ]
                    ).properties(height=300, title='Resiliência de Mercado')
                    st.altair_chart(chart_maturity, use_container_width=True)
                    
                    # Insight
                    if not df_maturity.empty:
                        total = df_maturity['count'].sum()
                        new_pct = (df_maturity[df_maturity['category'].str.contains('Novas')]['count'].sum() / total * 100) if total > 0 else 0
                        
                        if new_pct > 40:
                            st.info(f"**Mercado Vibrante:** {new_pct:.1f}% são novas entrantes (< 3 anos). Alta rotatividade e baixa barreira de entrada.")
                        elif new_pct < 15:
                            st.warning(f"**Mercado Consolidado:** Apenas {new_pct:.1f}% são novas. Dominado por veteranas. Alta barreira de entrada.")
                        else:
                            st.success(f"**Mercado Equilibrado:** {new_pct:.1f}% de novas empresas. Mix saudável entre inovação e experiência.")
                else:
                    st.info("Sem dados de idade disponíveis.")
            
            with c_nature:
                st.markdown("#### Grau de Formalização")
                st.caption("Distribuição por natureza jurídica.")
                
                df_nature = db.get_legal_nature_profile(**mi_filters)
                if not df_nature.empty:
                    chart_nature = alt.Chart(df_nature).mark_arc(innerRadius=60).encode(
                        theta=alt.Theta('count:Q'),
                        color=alt.Color('category:N', legend=alt.Legend(title='Tipo', orient='bottom'), scale=alt.Scale(
                            domain=['Sociedade Limitada (LTDA)', 'S.A. (Aberta/Fechada)', 'Empresário Individual', 'Empresa Pública/MEI', 'Outros'],
                            range=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
                        )),
                        tooltip=[
                            alt.Tooltip('category', title='Natureza'),
                            alt.Tooltip('count', title='Empresas', format=',d')
                        ]
                    ).properties(height=300, title='Estrutura Corporativa')
                    st.altair_chart(chart_nature, use_container_width=True)
                    
                    # Insight
                    if not df_nature.empty:
                        total = df_nature['count'].sum()
                        sa_pct = (df_nature[df_nature['category'].str.contains('S.A.')]['count'].sum() / total * 100) if total > 0 else 0
                        
                        if sa_pct > 20:
                            st.success(f"**Alta Sofisticação:** {sa_pct:.1f}% são S.A. (governança corporativa). Mercado profissionalizado.")
                        elif sa_pct < 5:
                            st.info(f"**Mercado Familiar:** Apenas {sa_pct:.1f}% de S.A. Dominado por LTDA (empresas familiares).")
                        else:
                            st.info(f"**Mix Corporativo:** {sa_pct:.1f}% de S.A. Equilíbrio entre estruturas familiares e profissionais.")
                else:
                    st.info("Sem dados de natureza jurídica disponíveis.")

            st.divider()

            # 5. Detailed Asset List (Unified View - No Rank)
            st.markdown("### Screen de Ativos (Geral)")
            
            df_disp = df_companies.copy()
            # Enrich Porte
            porte_map = {'00': 'N/D', '01': 'Micro', '03': 'Pequeno', '05': 'Médio/Gd'}
            if 'porte_empresa' in df_disp.columns:
                df_disp['Porte'] = df_disp['porte_empresa'].fillna('00').apply(lambda x: porte_map.get(str(x), str(x)))
            else: df_disp['Porte'] = '-'
            
            # Enrich Status
            if 'situacao_cadastral' in df_disp.columns:
                df_disp['Status'] = df_disp['situacao_cadastral'].apply(get_status_description)
            else: df_disp['Status'] = '-'
            
            # Enrich Type
            if 'identificador_matriz_filial' in df_disp.columns:
                df_disp['tipo_label'] = df_disp['identificador_matriz_filial'].map({'1': 'MATRIZ', '2': 'FILIAL'}).fillna('?')
            else: df_disp['tipo_label'] = '-'
            
            # Capital Format
            df_disp['Capital (R$)'] = df_disp['capital_social'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

            # Descriptions (Safe Get)
            if 'cnae_desc' not in df_disp.columns: df_disp['cnae_desc'] = df_disp.get('cnae_fiscal_principal', '-')
            if 'natureza_desc' not in df_disp.columns: df_disp['natureza_desc'] = df_disp.get('natureza_juridica', '-')

            st.dataframe(
                df_disp,
                height=500,
                width="stretch",
                column_order=["cnpj_real", "tipo_label", "razao_social", "Capital (R$)", "uf", "municipio", "Porte", "Status", "cnae_desc"],
                column_config={
                    "cnpj_real": st.column_config.TextColumn("CNPJ", width="medium"),
                    "tipo_label": st.column_config.TextColumn("Tipo", width="small"),
                    "razao_social": st.column_config.TextColumn("Razão Social", width="large"),
                    "Capital (R$)": st.column_config.TextColumn("Capital Social"),
                    "uf": "UF",
                    "municipio": "Cidade",
                    "Porte": "Porte",
                    "cnae_desc": st.column_config.TextColumn("Atividade Principal", width="medium")
                },
                hide_index=True
            )

        except Exception as e:
            st.error(f"Erro na análise de mercado: {e}")
