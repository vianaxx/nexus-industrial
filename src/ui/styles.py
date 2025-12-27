def get_custom_css():
    return """
    <style>
        /* Force Sidebar Width */
        [data-testid="stSidebar"] {
            min_width: 320px !important;
            width: 320px !important;
        }
        
        /* Clean Up Titles */
        h1 {
            padding-top: 0rem !important;
        }
    </style>
    """
