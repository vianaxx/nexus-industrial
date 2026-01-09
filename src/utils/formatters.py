"""
Formatadores numéricos padronizados para Nexus Industrial Intelligence.

Norma: ABNT NBR 5891 (Separadores brasileiros)
- Milhar: ponto (.)
- Decimal: vírgula (,)

Autor: Sistema
Data: 2026-01-08
Versão: 1.0
"""

def format_br_number(value: float, decimals: int = 0) -> str:
    """
    Formata número com separadores brasileiros.
    
    Args:
        value: Número a ser formatado
        decimals: Quantidade de casas decimais (padrão: 0)
    
    Returns:
        String formatada com separadores brasileiros
    
    Examples:
        >>> format_br_number(1234567, 0)
        '1.234.567'
        >>> format_br_number(1234.56, 2)
        '1.234,56'
    """
    formatted = f"{value:,.{decimals}f}"
    # Troca separadores: , -> X, . -> ,, X -> .
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def format_count(value: int, abbreviate: bool = True) -> str:
    """
    Formata contagem de itens (empresas, estabelecimentos, municípios).
    
    Args:
        value: Número inteiro a ser formatado
        abbreviate: Se True, abrevia valores >= 1.000.000
    
    Returns:
        String formatada
    
    Examples:
        >>> format_count(987)
        '987'
        >>> format_count(12345)
        '12.345'
        >>> format_count(1234567)
        '1,2 mi'
    """
    if abbreviate and value >= 1_000_000:
        return f"{value/1_000_000:,.1f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
    return format_br_number(value, decimals=0)


def format_currency(value: float, context: str = "kpi") -> str:
    """
    Formata valores monetários com prefixo R$.
    
    Args:
        value: Valor monetário
        context: Contexto de uso ("kpi", "tooltip", "table")
    
    Returns:
        String formatada com R$
    
    Examples:
        >>> format_currency(850000, "kpi")
        'R$ 850 mil'
        >>> format_currency(12400000, "kpi")
        'R$ 12,4 mi'
        >>> format_currency(1234567.89, "tooltip")
        'R$ 1.234.567,89'
    """
    # Handle negative values
    prefix = "R$ "
    if value < 0:
        prefix = "-R$ "
        value = abs(value)
    
    if context == "kpi":
        if value >= 1e9:
            return f"{prefix}{value/1e9:,.1f} bi".replace(",", "X").replace(".", ",").replace("X", ".")
        elif value >= 1e6:
            return f"{prefix}{value/1e6:,.1f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
        elif value >= 1e3:
            return f"{prefix}{value/1e3:,.0f} mil".replace(",", ".")
        else:
            return f"{prefix}{value:,.0f}".replace(",", ".")
    elif context == "tooltip":
        return f"{prefix}{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:  # table
        return f"{prefix}{value:,.0f}".replace(",", ".")


def format_percentage(value: float, precision: int = 1) -> str:
    """
    Formata percentuais com sufixo %.
    
    Args:
        value: Valor percentual (ex: 12.5 para 12,5%)
        precision: Casas decimais (padrão: 1)
    
    Returns:
        String formatada com %
    
    Examples:
        >>> format_percentage(12.5)
        '12,5%'
        >>> format_percentage(-3.2)
        '-3,2%'
        >>> format_percentage(12.345, 2)
        '12,35%'
    """
    return f"{value:.{precision}f}%".replace(".", ",")


def format_index(value: float, base_description: str = "") -> str:
    """
    Formata índices (Base 100, produção IBGE, etc).
    
    Args:
        value: Valor do índice
        base_description: Descrição da base (ex: "Base: Jan/2022 = 100")
    
    Returns:
        String formatada
    
    Examples:
        >>> format_index(98.7)
        '98,7'
        >>> format_index(104.3, "Base: Jan/2022 = 100")
        '104,3 (Base: Jan/2022 = 100)'
    """
    formatted = f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if base_description:
        return f"{formatted} ({base_description})"
    return formatted


def format_altair_axis(value: float, format_type: str = "number") -> str:
    """
    Formata valores para eixos de gráficos Altair.
    
    Args:
        value: Valor a ser formatado
        format_type: Tipo de formatação ("number", "currency", "percentage")
    
    Returns:
        String formatada para uso em labelExpr do Altair
    
    Examples:
        >>> format_altair_axis(1234567, "number")
        '1.234.567'
        >>> format_altair_axis(12.5, "percentage")
        '12,5%'
    """
    if format_type == "currency":
        return format_currency(value, context="kpi")
    elif format_type == "percentage":
        return format_percentage(value)
    else:
        return format_br_number(value, decimals=0)
