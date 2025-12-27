def get_custom_css():
    return """
    <style>
    /* Ajuste fino para sidebar, mas sem forçar largura fixa que quebra mobile */
    [data-testid="stSidebar"] {
        padding-top: 0rem;
    }
    
    /* Melhoria visual nos cards de métricas */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
    }
    
    /* Ajuste de espaçamento no topo */
    .block-container {
        padding-top: 2rem !important;
    }
    </style>
    """
