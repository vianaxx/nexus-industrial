def get_custom_css():
    return """
    <style>
    /* --- GLOBAL TYPOGRAPHY --- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    /* Headings - Use Streamlit's native text color */
    h1, h2, h3, h4, h5, h6, [data-testid="stHeader"] {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.025em !important;
        color: var(--text-color) !important;
    }
    
    h1 { font-size: 2.2rem !important; }
    h2 { font-size: 1.75rem !important; }
    h3 { font-size: 1.5rem !important; font-weight: 600 !important; }
    
    /* Body Text & Captions - Adaptive */
    p, li, .stMarkdown {
        font-size: 1rem;
        line-height: 1.6;
        color: var(--text-color);
    }
    
    small, .small-font, [data-testid="stCaption"] {
        font-size: 0.85rem !important;
        color: var(--text-color) !important;
        opacity: 0.7;
        font-weight: 400;
    }

    /* --- SIDEBAR STYLING (Theme-Aware) --- */
    [data-testid="stSidebar"] {
        background-color: var(--secondary-background-color);
        border-right: 1px solid rgba(128, 128, 128, 0.2);
        box-shadow: 2px 0 8px rgba(0,0,0,0.04);
    }

    /* Sidebar collapse button enabled */

    
    /* Headers & Footer Containers */
    .sidebar-header-container {
        margin-bottom: 1.5rem;
    }
    
    .sidebar-footer-container {
        margin-top: 3rem;
        padding: 1rem 0;
        border-top: 1px solid rgba(128, 128, 128, 0.2);
        text-align: center;
    }

    /* Modern Gradient Title (Adaptive) */
    .sidebar-title {
        font-size: 1.4rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: var(--text-color);
        margin-bottom: 0.2rem;
    }
    
    .sidebar-subtitle {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-color);
        opacity: 0.6;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    /* --- PAGE HEADER CLEANUP --- */
    .block-container {
        padding-top: 2rem !important;
        max-width: 95% !important;
    }

    /* --- METRIC CARDS (Theme-Aware) --- */
    div[data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease-in-out;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: var(--primary-color);
        border-width: 1px;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        color: var(--text-color) !important;
        opacity: 0.7;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.03em !important;
        color: var(--text-color) !important;
    }
    
    /* Table Headers */
    [data-testid="stDataFrame"] th {
        font-weight: 600 !important;
        color: var(--text-color) !important;
        font-size: 0.9rem !important;
    }
    
    /* Info/Warning/Success Boxes - Better contrast in Dark Mode */
    .stAlert {
        border-radius: 8px;
    }
    
    /* Expander - Theme aware */
    [data-testid="stExpander"] {
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 8px;
        background-color: var(--secondary-background-color);
    }
    </style>
    """
