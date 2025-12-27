# Nexus Industrial Brasil

> **Plataforma de Inteligência Industrial (CNAE B/C)**
> *Monitoramento Estratégico da Indústria Extrativa e de Transformação.*

O **Nexus Industrial Brasil** é uma solução de *Business Intelligence* que cruza dados oficiais da **Receita Federal (CNPJ)** com indicadores macroeconômicos do **IBGE (PIM-PF)** para revelar o ciclo real da indústria brasileira.

Diferente de ferramentas genéricas, esta plataforma foca exclusivamente nas **Seções B (Extrativa)** e **C (Transformação)** da CNAE, permitindo análises de alta precisão sobre a correlação entre novos investimentos (Abertura de Empresas) e produção física efetiva.

![Google BigQuery](https://img.shields.io/badge/Google_BigQuery-Cloud_Data_Warehouse-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red)
![IBGE](https://img.shields.io/badge/Dados-Oficiais-green)

---

## Pilares da Análise

A plataforma opera em 3 camadas complementares:

### 1. Estrutura de Mercado (Microeconomia)
*Fonte: Base CNPJ (Receita Federal) via BigQuery*
- **Quem são os players?** Mapeamento completo de indústrias ativas.
- **Market Share:** Concentração por setor (CNAE) e região (UF/Município).
- **Solidez:** Análise de Capital Social médio e porte das empresas.
- **Detalhe:** Lista granular de empresas com Situação Cadastral e Data de Abertura.

### 2. Atividade Industrial (Macroeconomia)
*Fonte: PIM-PF (IBGE API)*
- **O que está sendo produzido?** Volume físico real.
- **Diagnóstico de Ciclo:** Algoritmo que classifica o setor em 4 fases: *Expansão, Desaceleração, Recuperação ou Contração*.
- **Indicadores Premium:**
    - Índice Base Fixa (Nível e Sazonal)
    - Variação Mensal (Ritmo)
    - Acumulado 12 Meses (Tendência Estrutural)
- **Máquina do Tempo:** Seletor histórico para analisar dados de qualquer mês nos últimos 10 anos.

### 3. Dinâmica Estratégica (Correlação)
*Fonte: Cruzamento RFB x IBGE*
- **Investimento vs Produção:** O aumento no número de fábricas (CNPJ) está gerando mais produção (IBGE)? Ou é uma bolha?
- **Benchmark Regional:** Compare a performance do seu Estado com a média nacional.

---

## Arquitetura Técnica

O projeto utiliza uma arquitetura híbrida de alta performance:

1.  **Big Data (Nuvem):** A base de dados de CNPJs (Gigabytes) reside no **Google BigQuery**, permitindo filtros complexos em segundos sem consumir memória local.
2.  **API Live (Macro):** Dados do IBGE são consumidos em tempo real via API SIDRA.
3.  **Frontend (Local):** Interface Streamlit leve para visualização e interação.

---

## Instalação e Configuração

### Pré-requisitos
- Python 3.10+
- Conta no Google Cloud Plataform (GCP) com BigQuery habilitado.

### 1. Clone o Repositório
```bash
git clone https://github.com/seu-repositorio/nexus-industrial.git
cd nexus-industrial
```

### 2. Configure o Ambiente
Instale as dependências:
```bash
pip install -r requirements.txt
```

### 3. Credenciais do BigQuery
Para acessar o Data Warehouse, você precisa de uma chave de conta de serviço:
1.  No Console GCP, crie uma Service Account com permissão de `BigQuery Job User` e `BigQuery Data Viewer`.
2.  Baixe a chave JSON e salve na raiz do projeto como `service_account.json`.
3.  *(Opcional)* Configure variáveis de ambiente no `.env`:
    ```bash
    GCP_PROJECT_ID="seu-projeto-id"
    BQ_DATASET="seu_dataset"
    ```

### 4. Execute a Aplicação
```bash
streamlit run app.py
```

---

## Deploy no Streamlit Cloud (Grátis)

Este projeto está pronto para ser hospedado gratuitamente no **Streamlit Community Cloud**.

1.  Faça o Fork deste repositório no GitHub.
2.  Acesse [share.streamlit.io](https://share.streamlit.io) e conecte o repositório.
3.  **Configuração de Segredos (Secrets):**
    Como o projeto usa BigQuery, você **não** deve subir o arquivo `service_account.json` para o GitHub. Em vez disso, configure os segredos nas configurações do app no Streamlit Cloud:

    ```toml
    # .streamlit/secrets.toml
    
    [gcp_service_account]
    project_id = "seu-projeto-id"
    private_key = "-----BEGIN PRIVATE KEY-----\n..."
    client_email = "seu-email@..."
    # ... (copie todo o conteúdo do seu JSON aqui)
    ```

4.  O Streamlit detectará automaticamente o `requirements.txt` e instalará as dependências.

---

## Estrutura do Projeto

```
nexus-industrial/
├── app.py                  # Aplicação Principal
├── requirements.txt        # Dependências
├── service_account.json    # Credenciais (Ignorado no Git)
│
├── src/                    # Core da Aplicação
│   ├── database_bq.py      # Conector BigQuery (SQL Engine)
│   ├── ibge.py             # Conector IBGE (SIDRA API)
│   ├── ui/                 # Componentes de Interface
│   │   └── dashboard.py    # Lógica de Visualização
│   └── utils.py            # Formatadores e Helpers
│
└── scripts/                # Ferramentas de Manutenção
    ├── ingest_data_bq.py   # Carga de Dados para BigQuery
    └── legacy_sqlite/      # (Arquivado) Scripts da versão offline antiga
```

---

## Licença
Distribuído sob a licença MIT. Sinta-se livre para adaptar para seu setor.
