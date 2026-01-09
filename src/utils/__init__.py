"""
Utilities module for Nexus Industrial Intelligence.
"""

# Legacy utility functions (from old utils.py)
from .legacy import (
    format_cnpj,
    format_currency,
    format_date,
    get_status_description,
    format_cnae
)

# New Brazilian number formatters (ABNT NBR 5891)
from .formatters import (
    format_br_number,
    format_count,
    format_currency as format_currency_br,
    format_percentage,
    format_index,
    format_altair_axis
)

__all__ = [
    # Legacy functions
    'format_cnpj',
    'format_currency',
    'format_date',
    'get_status_description',
    'format_cnae',
    # New formatters
    'format_br_number',
    'format_count',
    'format_currency_br',
    'format_percentage',
    'format_index',
    'format_altair_axis'
]
