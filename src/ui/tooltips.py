# Dicionário de Tooltips - Nexus Industrial Intelligence
# Contém textos explicativos para KPIs, Gráficos e Filtros.

TOOLTIPS = {
    # --- FILTROS ---
    "cnae_subclasse": """
    **O que é:** Classificação Nacional de Atividades Econômicas (Nível 7 dígitos).
    **Como é construído:** Baseado no cadastro principal da Receita Federal (RFB).
    **Como interpretar:** Define a atividade 'core' da empresa.
    **Atenção:** Autodeclaratório na abertura da empresa.
    """,
    
    "porte": """
    **O que é:** Classificação de tamanho tributário (ME, EPP ou Demais).
    **Como é construído:** Baseado no cadastro da Receita Federal. 'Demais' inclui médias e grandes.
    **Como interpretar:** Proxy de tamanho e regime tributário.
    **Atenção:** Não reflete necessariamente o faturamento atual.
    """,
    
    "escopo_geo": """
    **O que é:** Distinção entre sede (Matriz) e unidade operacional (Filial).
    **Como interpretar:** Matrizes = Decisão. Filiais = Expansão física.
    """,

    # --- MICRO (ESTRUTURA) ---
    "kpi_ativos": """
    **O que é:** Total de CNPJs com situação 'Ativa'.
    **Como interpreta:** Capacidade instalada total (Matrizes + Filiais).
    **Atenção:** Inclui empresas ativas na RFB mesmo sem produção momentânea.
    """,
    
    "kpi_capital_medio": """
    **O que é:** Média do Capital Social dos estabelecimentos.
    **Como interpreta:** Indicador de robustez financeira e barreira de entrada.
    **Atenção:** NÃO É FATURAMENTO. Reflete investimento societário.
    """,

    "kpi_concentracao": """
    **O que é:** Percentual do mercado detido pelo líder (Top 1).
    **Como interpreta:** Mede grau de monopólio ou domínio regional.
    """,

    "kpi_setor_lider": """
    **O que é:** Segmento com maior número de estabelecimentos.
    **Como interpreta:** Indica a vocação principal da região ou filtro.
    """,
        
    "chart_ranking_capital": """
    **O que é:** Top 10 empresas (Matrizes) por Capital Social.
    **Como interpreta:** Identifica líderes de capacidade de investimento.
    **Atenção:** Não é ranking de vendas/receita.
    """,

    "chart_maturidade": """
    **O que é:** Perfil etário das empresas (Idade da fundação).
    **Como interpreta:** Mercados com muitas 'Novas' são vibrantes. Mercados 'Veteranos' são consolidados.
    """,

    # --- MACRO (ATIVIDADE) ---
    "kpi_indice_base": """
    **O que é:** Volume físico de produção (Base 2022=100).
    **Como interpreta:** Nível Real de Atividade. Se > 100, produziu mais que a média de 2022.
    """,
    
    "kpi_ritmo": """
    **O que é:** Var. Mensal com ajuste sazonal.
    **Como interpreta:** O 'Pulso' de curto prazo. Mostra aceleração/frenagem imediata.
    """,
    
    "kpi_tendencia": """
    **O que é:** Acumulado nos últimos 12 meses.
    **Como interpreta:** A Direção Estrutural do ciclo (Longo Prazo).
    """,
    
    "kpi_yoy": """
    **O que é:** Comparação Ano contra Ano (ex: Out/25 vs Out/24).
    **Como interpreta:** Desempenho contra uma base sazonalmente comparável.
    """,
    
    "chart_scatter": """
    **O que é:** Mapa de Ciclo (Ritmo vs Tendência).
    **Como interpreta:**
    - Q1 (Dir/Sup): Expansão.
    - Q2 (Dir/Inf): Desaceleração.
    - Q3 (Esq/Inf): Contração.
    - Q4 (Esq/Sup): Recuperação.
    """,
    
    "kpi_correlacao": """
    **O que é:** Sincronia entre Abertura de Empresas e Produção Industrial.
    **Como interpreta:** +1 (Totalmente Sincronizado), 0 (Sem relação), -1 (Inverso).
    **Atenção:** Pode haver defasagem temporal (time lag).
    """
}
