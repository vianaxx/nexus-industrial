import requests
import time

BASE_URL = "https://servicodados.ibge.gov.br/api/v3/agregados/8888"

# Range to probe: generic industry is 129314, food is 129317. 
# Suspect Extractive is in between or nearby. 
# Also checking 129300-129313 just in case.
# And 05-09 ranges.

candidate_ids = list(range(129310, 129330))

print(f"Probing {len(candidate_ids)} IDs...")

found = {}

for cid in candidate_ids:
    # Use variable 11601 (Monthly Var) just to get metadata header
    url = f"{BASE_URL}/periodos/-1/variaveis/11601?localidades=N1[all]&classificacao=544[{cid}]"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                # Extract category name
                # Structure: [ { "resultados": [ { "classificacoes": [ { "categoria": { "129314": { "nome": "..." } } } ] } ] } ]
                try:
                    res = data[0]['resultados'][0]
                    clas = res['classificacoes'][0]
                    cat = clas['categoria']
                    name = cat.get(str(cid), {}).get('nome', 'Unknown')
                    print(f"[FOUND] {cid}: {name}")
                    found[cid] = name
                except:
                    print(f"[ERROR PARSING] {cid}")
            else:
                pass # Empty data
        else:
            pass # 404 or other
    except Exception as e:
        print(f"[EXCEPTION] {cid}: {e}")
    
    time.sleep(0.5) # Be gentle

print("\n--- SUMMARY ---")
for k, v in found.items():
    print(f"'{k}': '{v}'")
