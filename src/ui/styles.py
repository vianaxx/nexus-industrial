def get_custom_css():
    return """
    <style>
    [data-testid="stSidebar"] {
        min-width: 320px;
        max-width: 320px;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem;
    }
    </style>
    """
