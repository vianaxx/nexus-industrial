def format_cnpj(cnpj: str) -> str:
    if not cnpj:
        return ""
    clean_cnpj = str(cnpj).strip()
    if len(clean_cnpj) <= 8:
        return f"{clean_cnpj[:2]}.{clean_cnpj[2:5]}.{clean_cnpj[5:8]}"
    elif len(clean_cnpj) == 14:
        return f"{clean_cnpj[:2]}.{clean_cnpj[2:5]}.{clean_cnpj[5:8]}/{clean_cnpj[8:12]}-{clean_cnpj[12:14]}"
    else:
        return clean_cnpj

def format_currency(value: float) -> str:
    if not value and value != 0:
        return ""
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"

def format_date(date_str: str) -> str:
    if not date_str or len(date_str) != 8:
        return date_str
    return f"{date_str[6:8]}/{date_str[4:6]}/{date_str[:4]}"

def get_status_description(code: str) -> str:
    mapping = {
        '01': 'NULA',
        '02': 'ATIVA',
        '03': 'SUSPENSA',
        '04': 'INAPTA',
        '08': 'BAIXADA'
    }
    return mapping.get(str(code), code)

def format_cnae(code: str) -> str:
    """Formats a 7-digit CNAE code to XX.XX-X/XX standard."""
    c = str(code).strip()
    if len(c) == 7:
        return f"{c[:2]}.{c[2:4]}-{c[4]}/{c[5:]}"
    return c
