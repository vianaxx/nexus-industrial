"""
Centralized Tooltip Definitions for Nexus Industrial Dashboard.

Princípios de Design:
1. Clareza Imediata (< 3s de leitura)
2. Linguagem Natural (Human-first)
3. Função Pedagógica (Ensina a ler o dado)
4. Neutralidade Analítica (Estrutura vs Dinâmica)

Format: "O que é", "Como interpretar", "O que não significa", "Metodologia"
"""

TOOLTIPS = {
    # --- SECTION A: STRUCTURE (MICRO VIEW) ---
    
    "kpi_active_companies": """
    **O que mostra:** Contagem total de unidades produtivas (CNPJs) com status "Ativo" na Receita Federal.
    \n**Como interpretar:** Representa o tamanho da "mancha industrial". Alta densidade indica clusters competitivos; baixa densidade pode indicar nichos ou menor atratividade.
    \n**O que NÃO significa:** Não reflete saúde financeira ou volume de produção atual. Inclui empresas que podem não estar operando fatidicamente.
    """,
    
    "kpi_avg_capital": """
    **O que mostra:** Média aritmética do Capital Social declarado pelas empresas selecionadas.
    \n**Como interpretar:** É um proxy de **Robustez e Barreira de Entrada**. Setores de capital alto (Ex: Refino) exigem infraestrutura pesada. Capital baixo sugere setores de serviços ou manufatura leve.
    \n**O que NÃO significa:** NÃO é faturamento nem valor de mercado (Valuation). É o investimento dos sócios na constituição.
    """,
    
    "kpi_concentration": """
    **O que mostra:** O peso percentual do líder (Top 1 categoria) em relação ao todo.
    \n**Como interpretar:** Mede a **Dependência**. Acima de 50% sugere "Monocultura" (alta vulnerabilidade). Abaixo de 20% indica diversificação e resiliência.
    \n**O que NÃO significa:** Concentração alta não é necessariamente ruim; pode indicar um Cluster de Especialização eficiente (Ex: Calçados em Franca).
    """,
    
    "kpi_setor_lider": """
    **O que mostra:** O setor (ou estado) com maior número de estabelecimentos na seleção atual.
    \n**Como interpretar:** Identifica a **vocação principal** do recorte analisado.
    \n**O que NÃO significa:** Liderança em *quantidade* de empresas não garante liderança em *faturamento* ou *lucro*.
    """,

    # --- SECTION B: DYNAMICS (MACRO VIEW) ---

    "kpi_indice_base": """
    **O que mostra:** Volume físico produzido normalizado (Base: Média 2022 = 100).
    \n**Como interpretar:** É o "termômetro de nível". Se valor = 110, a produção está 10% acima da média de 2022. Permite comparar volumes reais descontando inflação.
    \n**O que NÃO significa:** Não é valor monetário de vendas, mas sim quantidade física (toneladas, unidades).
    """,

    "kpi_ritmo": """
    **O que mostra:** Aceleração de curto prazo (Mês Atual vs Mês Anterior), com ajuste sazonal.
    \n**Como interpretar:** Detecta **Inflexões**. É o primeiro a reagir a mudanças. Positivo (>0) = Acelerando; Negativo (<0) = Desacelerando.
    \n**O que NÃO significa:** Um mês negativo não decreta crise; pode ser ajuste pontual. Olhe a tendência de 12 meses para confirmar.
    """,

    "kpi_yoy": """
    **O que mostra:** Desempenho relativo ao mesmo mês do ano anterior (Ex: Out/25 vs Out/24).
    \n**Como interpretar:** Elimina o ruído sazonal (vendas de Natal comparadas com Natal). É a métrica padrão de mercado para avaliar crescimento real.
    \n**O que NÃO significa:** Não mostra a trajetória mês a mês, apenas o "salto" de um ano para o outro.
    """,

    "kpi_tendencia": """
    **O que mostra:** Acumulado dos últimos 12 meses vs 12 meses anteriores.
    \n**Como interpretar:** Mostra a **Direção Estrutural** do ciclo. Suaviza oscilações de curto prazo e revela se o setor está em expansão ou contração sustentada.
    \n**O que NÃO significa:** Reage lentamente. Pode continuar positivo logo no início de uma crise (inércia estatística).
    """,

    "kpi_correlacao": """
    **O que mostra:** Grau de sincronia entre a abertura de empresas (Micro) e a produção física (Macro).
    \n**Como interpretar:**
    *   **Alta (Clara):** O ânimo do empreendedor segue a produção industrial.
    *   **Baixa (Sem Relação):** O setor de investimento descolou da realidade fabril (Bolha ou Oportunidade?).
    """,

    # --- SECTION C: CHARTS ---

    "chart_geo": """
    **O que mostra:** Distribuição dos estabelecimentos por Unidade Federativa.
    \n**Como interpretar:** Revela a **Geografia Econômica**. Barras maiores indicam os "Hubs" produtivos.
    \n**Nota:** Limitado ao Top 10 para focar nos clusters relevantes.
    """,

    "chart_sector": """
    **O que mostra:** Quantidade de empresas quebrada por divisão industrial (CNAE).
    \n**Como interpretar:** Mostra o **Perfil Vocacional**. Uma base diversificada (várias barras médias) é mais resiliente que uma base concentrada (uma barra gigante).
    \n**Dica:** Use o filtro de CNAE para aprofundar nos nichos.
    """,

    "chart_ranking_capital": """
    **O que mostra:** O Top 10 empresas (Matrizes) ordenadas pelo Capital Social declarado.
    \n**Como interpretar:** Identifica os **"Campeões Nacionais"** ou regionais. Empresas com capital social alto possuem maior capacidade de investimento e solvência.
    \n**O que NÃO significa:** Não reflete o faturamento anual (Receita), mas sim o patrimônio investido.
    """,

    "chart_maturidade": """
    **O que mostra:** Classificação das empresas pelo tempo de vida (Data de Abertura).
    \n**Como interpretar:**
    *   **Novas (<3 anos):** Inovação, mas alto risco de mortalidade.
    *   **Consolidadas (10+ anos):** Resiliência provada. Base da estabilidade econômica.
    \n**Uso:** Avaliar se o setor é "Jovem/Vibrante" ou "Maduro/Envelhecido".
    """,

    "chart_evolution": """
    **O que mostra:** Histórico de abertura de novas empresas (CNPJs) ao longo do tempo.
    \n**Como interpretar:**
    *   **Tendência de Alta:** "Corrida do Ouro" (oportunidade percebida) ou baixa barreira de entrada.
    *   **Tendência de Baixa:** Saturação, incerteza econômica ou consolidação (M&A).
    \n**O que NÃO significa:** Abertura de CNPJ não gera produção imediata (existe um tempo de maturação).
    """,
    
    "chart_scatter": """
    **O que mostra:** Matriz Estratégica cruzando Ritmo (Curto Prazo) vs Tendência (Longo Prazo).
    \n**Como interpretar os Quadrantes:**
    *   **↗️ Expansão (Sup. Dir):** Cresce agora e já vinha crescendo. Melhor cenário.
    *   **↘️ Desaceleração (Inf. Dir):** Tendência boa, mas perdeu fôlego recente. Atenção.
    *   **↖️ Recuperação (Sup. Esq):** Vinha mal, mas reagiu forte agora. Oportunidade.
    *   **↙️ Contração (Inf. Esq):** Cai no curto e no longo prazo. Crise.
    \n**O que NÃO significa:** Posição não é destino. Setores se movem no sentido horário ao longo do ciclo econômico.
    """,

    # --- SECTION D: FILTERS & CONCEPTS ---
    
    "filter_cnae": """
    **Conceito:** Classificação Nacional de Atividades Econômicas.
    \n**Hierarquia:** 
    *   **Divisão (2 dígitos):** O setor amplo (Ex: Alimentos).
    *   **Classe (5 dígitos):** O nicho (Ex: Fabricação de Suco).
    \n**Uso:** Use a hierarquia para fazer "drill-down" do macro para o micro.
    """,
    "cnae_subclasse": """
    **Conceito:** Subclasse CNAE (Nível mais detalhado).
    \n**Definição:** Identifica com precisão máxima a atividade econômica (7 dígitos).
    \n**Uso:** Ideal para nichos específicos (Ex: Fabricação de Suco de Laranja Concentrado).
    """,
    
    "filter_natureza": """
    **Conceito:** A constituição legal da empresa.
    \n**Leitura:** 
    *   **S.A.:** Geralmente grandes corporações, governança rígida.
    *   **LTDA:** Estrutura mais comum, de médias a gigantes familiares.
    *   **MEI:** Empreendedor individual, alta informalidade.
    """,
    
    "filter_scope": """
    **Conceito:** Diferenciação funcional da unidade.
    \n**Matriz:** Sede administrativa (Decisões, Compras Corporativas).
    \n**Filial:** Unidade operacional ou ponto de venda (Capilaridade).
    \n**Todos:** Visão completa da presença física.
    """,
    
    "escopo_geo": """
    **Conceito:** Diferenciação funcional da unidade.
    \n**Matriz:** Sede administrativa (Decisões, Compras Corporativas).
    \n**Filial:** Unidade operacional ou ponto de venda (Capilaridade).
    \n**Todos:** Visão completa da presença física.
    """,
    
    "porte": """
    **Conceito:** Tamanho da empresa (Receita Bruta Anual).
    \n**ME (Micro):** Até R$ 360 mil.
    \n**EPP (Pequeno Porte):** De R$ 360 mil até R$ 4,8 milhões.
    \n**Demais (Médio/Grande):** Acima de R$ 4,8 milhões (S.A.s e Ltda de grande porte).
    """
}
