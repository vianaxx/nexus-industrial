def get_custom_css():
    return """
    <style>
    /* --- GLOBAL TYPOGRAPHY --- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        color: #1e293b;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6, [data-testid="stHeader"] {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.025em !important;
        color: #0f172a !important;
    }
    
    h1 { font-size: 2.2rem !important; }
    h2 { font-size: 1.75rem !important; }
    h3 { font-size: 1.5rem !important; font-weight: 600 !important; }
    
    /* Body Text & Captions */
    p, li, .stMarkdown {
        font-size: 1rem;
        line-height: 1.6;
        color: #334155;
    }
    
    small, .small-font, [data-testid="stCaption"] {
        font-size: 0.85rem !important;
        color: #64748b !important;
        font-weight: 400;
    }

    /* --- SIDEBAR STYLING --- */
    [data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
        box-shadow: 2px 0 8px rgba(0,0,0,0.04);
    }

    /* Ocultar botão de fechar (Lock Sidebar Open) */
    [data-testid="stSidebarCollapseButton"] {
        display: none;
    }
    
    /* Headers & Footer Containers */
    .sidebar-header-container {
        margin-bottom: 1.5rem;
    }
    
    .sidebar-footer-container {
        margin-top: 3rem;
        padding: 1rem 0;
        border-top: 1px solid #e2e8f0;
        text-align: center;
    }

    /* Modern Gradient Title */
    .sidebar-title {
        font-size: 1.4rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .sidebar-subtitle {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    /* --- PAGE HEADER CLEANUP --- */
    .block-container {
        padding-top: 2rem !important;
        max-width: 95% !important;
    }

    /* --- METRIC CARDS --- */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #eff6ff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease-in-out;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #bfdbfe;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        color: #64748b !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.03em !important;
        color: #1e293b !important;
    }
    
    /* Table Headers */
    [data-testid="stDataFrame"] th {
        font-weight: 600 !important;
        color: #334155 !important;
        font-size: 0.9rem !important;
    }
    </style>
    """
