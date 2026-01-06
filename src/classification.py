def get_industrial_typology(cnae_code):
    """
    Maps a CNAE code (string) to Industrial Typology and Value Chain Position.
    Returns a dict: {'tipo_industria': '...', 'cadeia_valor': '...'}
    """
    if not cnae_code:
        return {'tipo_industria': 'Não Identificado', 'cadeia_valor': 'Não Identificado'}
    
    # Ensure 2 digits
    code_str = str(cnae_code).replace(".", "").replace("-", "").strip()
    if len(code_str) < 2:
        return {'tipo_industria': 'Não Identificado', 'cadeia_valor': 'Não Identificado'}
        
    div = int(code_str[:2])
    
    # 1. TIPO DE INDÚSTRIA (Industrial Type)
    # Extrativa (05-09)
    if 5 <= div <= 9:
        tipo = "Indústria Extrativa"
        cadeia = "Upstream"
        
    # Bens de Consumo Não Duráveis (10-15, 18, 32)
    # 10: Alimentos, 11: Bebidas, 12: Fumo, 13: Têxtil, 14: Vestuário, 15: Couros, 18: Impressão, 32: Diversos
    elif div in [10, 11, 12, 13, 14, 15, 18, 32]:
        tipo = "Bens de Consumo Não Duráveis"
        cadeia = "Downstream"

    # Intermediária / Insumos (16, 17, 19-23)
    # 16: Madeira, 17: Celulose, 19: Coque/Petróleo, 20: Químicos, 21: Farmo (Mix), 22: Borracha, 23: Minerais não-met.
    elif div in [16, 17, 19, 20, 21, 22, 23]:
        tipo = "Indústria Intermediária"
        cadeia = "Midstream"

    # Indústria de Base (24, 25)
    # 24: Metalurgia, 25: Produtos de Metal
    elif div in [24, 25]:
        tipo = "Indústria de Base"
        cadeia = "Midstream"

    # Bens de Consumo Duráveis (29, 31)
    # 29: Veículos (Final), 31: Móveis
    elif div in [31]: # Veiculos is complex, treated below
        tipo = "Bens de Consumo Duráveis"
        cadeia = "Downstream"

    # Bens de Capital / Complexo Eletrônico (26, 27, 28, 29, 30, 33)
    # 26: Informática, 27: Elétrico, 28: Máquinas, 29: Veículos, 30: Outros transportes, 33: Manutenção
    elif div in [26, 27, 28, 29, 30, 33]:
        # Refinement for Vehicles (29) - Usually Durable Goods, but heavily Capital too. 
        # IBGE classifies Cars as Durable Goods. Trucks as Capital.
        # For simplicity in Level 1, we map:
        if div == 29: 
             tipo = "Bens de Consumo Duráveis" # Autos
             cadeia = "Downstream"
        elif div == 28:
             tipo = "Bens de Capital"
             cadeia = "Upstream" # or Midstream provider
        else:
             tipo = "Bens de Capital"
             cadeia = "Midstream"
    else:
        tipo = "Outros"
        cadeia = "N/A"

    return {'tipo_industria': tipo, 'cadeia_valor': cadeia}

def get_divisions_for_typology(typology):
    """Returns a list of integer divisions for a given typology filter."""
    mapping = {
        "Indústria Extrativa": list(range(5, 10)),
        "Bens de Consumo Não Duráveis": [10, 11, 12, 13, 14, 15, 18, 32],
        "Indústria Intermediária": [16, 17, 19, 20, 21, 22, 23],
        "Indústria de Base": [24, 25],
        "Bens de Consumo Duráveis": [29, 31],
        "Bens de Capital": [26, 27, 28, 30, 33]
    }
    return mapping.get(typology, [])

def get_divisions_for_value_chain(chain_pos):
    """Returns list of divisions for Upstream/Midstream/Downstream."""
    results = []
    # Loop over all industrial divisions
    for div in range(5, 34):
        res = get_industrial_typology(str(div).zfill(2))
        if res.get('cadeia_valor') == chain_pos:
            results.append(div)
    return results
