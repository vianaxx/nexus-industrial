# ☁️ Guia de Configuração: Google BigQuery

Este guia passo-a-passo vai te ensinar a configurar o Google Cloud para hospedar seu banco de dados de CNPJs de graça.

---

## 1. Criar o Projeto no Google Cloud
1.  Acesse o [Console do Google Cloud](https://console.cloud.google.com/).
2.  Faça login com sua conta Google.
    *   *Nota: Se for a primeira vez, ele vai pedir para aceitar os termos e cadastrar um cartão de crédito. Isso é obrigatório para verificar que você não é um robô, mas o plano "Free Tier" não cobra nada se você ficar dentro dos limites (que são altos).*
3.  No topo da tela, clique na lista de projetos (geralmente diz "My First Project") e clique em **"Novo Projeto"**.
4.  Dê um nome, exemplo: `cnpj-nexus-db`.
5.  Clique em **Criar** e aguarde uns segundos. Depois selecione o projeto recém-criado.

## 2. Ativar o BigQuery
1.  Na barra de busca no topo, digite **"BigQuery"**.
2.  Selecione "BigQuery" nos resultados.
3.  No menu esquerdo, você verá seu projeto. Clique nos três pontinhos (`...`) ao lado do nome do projeto -> **Criar conjunto de dados** (Create dataset).
4.  **ID do conjunto de dados:** Digite `cnpj_raw`.
5.  **Local do dados:** Escolha `us-east1` (Carolina do Sul) ou `southamerica-east1` (São Paulo). *Dica: US geralmente é mais barato ou tem mais cota grátis, mas SP é mais rápido.*
6.  Clique em **Criar conjunto de dados**.

## 3. Criar a "Chave do Cofre" (Service Account)
Para que nosso script em Python consiga entrar no Google e ler os dados, precisamos de uma chave.

1.  Na busca do topo, digite **"IAM e Admin"** e selecione.
2.  No menu esquerdo, clique em **Contas de serviço**.
3.  Clique em **+ CIBER CONTA DE SERVIÇO** (Create Service Account).
    *   **Nome:** `cnpj-app-user`.
    *   Clique em **Criar e Continuar**.
4.  **Papel (Role):** Procure por "BigQuery" e selecione **"Administrador do BigQuery"** (ou BigQuery Admin).
    *   *Isso dá permissão para ler e escrever dados.*
    *   Clique em **Continuar** e depois **Concluir**.
5.  Agora, na lista, clique na conta que você acabou de criar (no email dela).
6.  Vá na aba **CHAVES** (Keys).
7.  Clique em **Adicionar Chave** -> **Criar nova chave**.
8.  Escolha o tipo **JSON** e clique em **Criar**.
9.  🚨 **UM ARQUIVO SERÁ BAIXADO NO SEU PC.**
    *   Esse arquivo é a chave mestra. **Não mande para ninguém.**
    *   Salve ele numa pasta segura com o nome `service_account.json`.

## 4. Subir os Dados (Via Google Cloud Storage)
Como os arquivos são gigantes (o navegador não aguenta o upload direto), vamos usar o **Storage** como ponte.

### Passo A: Criar um Bucket (Balde)
1.  No menu do Google Cloud, procure por **"Cloud Storage"** -> **Buckets**.
2.  Clique em **Criar Bucket**.
3.  Dê um nome único (ex: `cnpj-arquivos-brutos-seunome`).
4.  **Localização:** Escolha a mesma região do BigQuery (`us-east1` ou `southamerica-east1`).
5.  Clique em **Criar**.

### Passo B: Enviar os arquivos
1.  Dentro do bucket criado, clique em **Fazer Upload de Arquivos**.
2.  Selecione todos os seus CSVs (`K32...EMPRECSV`, `NATJUCSV`, etc).
3.  Vá tomar um café ☕. Isso vai depender da sua internet.
    *   *Dica: Se sua internet for lenta, comece subindo só o Y1 e os arquivos pequenos (NATJUCSV) para testar.*

### Passo C: Importar para o BigQuery
1.  Volte para o **BigQuery**.
2.  Clique no seu dataset `cnpj_raw`.
3.  Clique em **Criar Tabela**.
4.  **Criar tabela a partir de:** Escolha **Google Cloud Storage**.
5.  Clique em **Procurar** e selecione o arquivo CSV lá no seu bucket (ex: `...Y1...EMPRECSV`).
6.  **Formato:** CSV.
7.  **Nome da tabela:** `empresas`.
8.  **Esquema:** Marque **Detectar Automaticamente**.
9.  **Opções Avançadas:**
    *   Delimitador: `;` (ponto e vírgula).
    *   Linhas de cabeçalho para pular: 0.
    *   **Importante:** Se for adicionar múltiplos arquivos na mesma tabela, na próxima vez escolha a opção **"Anexar à tabela"** (Append) em vez de criar nova.

---

### Próximos Passos no Código
Depois que você tiver feito isso e tiver o arquivo `service_account.json`, me avise! Vamos configurar o projeto para usar essa chave.
