# Portal Logístico — Rastreamento de Frota

Portal web em Python + Streamlit para análise de rastreamento GPS de frota.
O sistema carrega CSVs de coordenadas, consolida os dados em DuckDB, calcula
KPIs, gera gráficos Plotly, exibe mapas interativos com PyDeck e permite análises
por veículo e por período.

---

## 1. Sobre o projeto

| Componente | Tecnologia |
|------------|-----------|
| Interface  | Streamlit  |
| Banco de dados | DuckDB (em disco local ou temporário no Cloud) |
| Mapas | PyDeck (WebGL via deck.gl) |
| Gráficos | Plotly |
| Storage dos CSVs | Google Drive (Cloud) ou `data/uploads/` (local) |

### Páginas disponíveis

| Página | Descrição |
|--------|-----------|
| Dashboard Geral | KPIs, km por veículo, evolução diária, ranking de alertas, heatmap de atividade |
| Mapa de Rotas | Mapa interativo por dia e veículo com cores por faixa de velocidade |
| Análise por Veículo | KPIs individuais, gráficos diários, exportação para Excel |
| Histórico | Comparativo entre dois períodos com variação percentual |
| Upload de Dados | Envio, validação, listagem e remoção de CSVs |

---

## 2. Como rodar localmente

### Pré-requisitos

- Python 3.11 ou superior
- Git

### Instalação

```bash
git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
cd SEU_REPOSITORIO
python -m venv .venv
```

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
source .venv/bin/activate
```

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Configuração do `secrets.toml` (somente se usar Google Drive)

Copie o template e preencha com os valores reais:

```bash
cp .streamlit/secrets.toml .streamlit/secrets.toml.template  # mantém backup
# edite .streamlit/secrets.toml com seus valores
```

> **⚠️ Nunca versione o `secrets.toml` com valores reais no Git.**

### Iniciar o portal

```bash
streamlit run app.py
```

Acesse em: `http://localhost:8501`

### Modo sem Google Drive (local puro)

Sem o `secrets.toml` ou sem a seção `[google_drive]`, o portal funciona
completamente offline: os CSVs são salvos em `data/uploads/` e o DuckDB em
`data/frota.duckdb`.

---

## 3. Como configurar o Google Drive

### 3.1 — Criar projeto no Google Cloud Console

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Clique em **Selecionar projeto → Novo projeto**
3. Dê um nome (ex.: `portal-logistico`) e clique em **Criar**

### 3.2 — Ativar a Google Drive API

1. No menu lateral: **APIs e serviços → Biblioteca**
2. Pesquise por **Google Drive API** e clique em **Ativar**

### 3.3 — Criar Service Account e baixar a chave JSON

1. Vá em **IAM e administrador → Contas de serviço**
2. Clique em **Criar conta de serviço**
3. Preencha o nome (ex.: `portal-frota`) e clique em **Criar e continuar**
4. Na etapa de permissões, clique em **Continuar** (sem papel necessário)
5. Clique em **Concluído**
6. Clique na conta de serviço criada → aba **Chaves** → **Adicionar chave → Criar nova chave → JSON**
7. Salve o arquivo `.json` baixado em local seguro

### 3.4 — Compartilhar a pasta do Drive com a Service Account

1. Crie (ou selecione) uma pasta no Google Drive que guardará os CSVs
2. Clique com o botão direito na pasta → **Compartilhar**
3. No campo de e-mail, cole o valor do campo `client_email` do JSON baixado
4. Defina permissão como **Editor** e clique em **Enviar**
5. Copie o **ID da pasta**: ele aparece na URL do Drive após `/folders/`
   Ex.: `https://drive.google.com/drive/folders/1AbCdEfGhIjKl` → ID: `1AbCdEfGhIjKl`

### 3.5 — Preencher o `secrets.toml`

Abra `.streamlit/secrets.toml` e preencha com os campos do JSON baixado:

```toml
[google_drive]
type             = "service_account"
project_id       = "seu-projeto-id"          # campo "project_id" do JSON
private_key_id   = "abc123..."               # campo "private_key_id" do JSON
private_key      = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email     = "portal-frota@seu-projeto.iam.gserviceaccount.com"
client_id        = "123456789"               # campo "client_id" do JSON
auth_uri         = "https://accounts.google.com/o/oauth2/auth"
token_uri        = "https://oauth2.googleapis.com/token"
folder_id        = "1AbCdEfGhIjKl"           # ID da pasta do Drive
```

> **Atenção:** copie `private_key` exatamente como está no JSON, incluindo os
> `\n` literais — o portal converte automaticamente para quebras de linha reais.

---

## 4. Como fazer deploy no Streamlit Community Cloud

### 4.1 — Publicar o código no GitHub

```bash
git init                          # se ainda não for um repositório
git add .
git commit -m "Portal logístico — versão inicial"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

> O `.gitignore` já exclui `secrets.toml`, `*.duckdb` e `data/uploads/*.csv`.

### 4.2 — Criar o app no Streamlit Community Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io) e faça login com GitHub
2. Clique em **New app**
3. Selecione o repositório e a branch (`main`)
4. Defina o arquivo principal: `app.py`
5. Clique em **Advanced settings** (próximo passo antes de deployar)

### 4.3 — Configurar os Secrets no painel

1. Na tela de **Advanced settings**, clique na aba **Secrets**
2. Cole o conteúdo completo do seu `secrets.toml` local (com valores reais)
3. Clique em **Save**

### 4.4 — Fazer o deploy

1. Clique em **Deploy!**
2. Aguarde a instalação das dependências (1–3 minutos)
3. O app ficará disponível em `https://seu-usuario-seu-repositorio-main.streamlit.app`

### 4.5 — Atualizações futuras

Basta fazer `git push origin main` — o Streamlit Cloud detecta automaticamente
e redeploya o app.

---

## 5. Como adicionar novos CSVs

### Via portal (recomendado)

1. Abra o portal e acesse **Upload de Dados** no menu lateral
2. Clique em **Browse files** e selecione um ou mais CSVs
3. O portal valida as colunas, descarta coordenadas inválidas e:
   - **Modo Drive:** envia para a pasta do Google Drive configurada
   - **Modo local:** salva em `data/uploads/`
4. Os dados ficam disponíveis imediatamente nas demais páginas

### Formato esperado do CSV

O arquivo deve conter exatamente estas colunas (separador `,` ou `;`):

```
Veículo | Placa | Organização | Data da Coordenada | Data da Gravação |
Velocidade | Ignição | Serial | Posição
```

A coluna `Posição` deve estar no formato `latitude,longitude`:
```
"-3.789100,-38.512300"
```

Datas no formato brasileiro: `dd/mm/aaaa HH:MM:SS`

---

## 6. Uso via linha de comando (CLI)

O fluxo CLI foi preservado em `main_cli.py` para geração de relatórios e mapas
HTML fora do Streamlit:

```bash
python main_cli.py \
  --arquivo "data/uploads/arquivo.csv" \
  --data 09/05/2026 \
  --veiculo 1060
```

Adicione `--sem-mapa` para pular a geração do mapa HTML (mais rápido).

---

## 7. Estrutura do projeto

```
├── app.py                  # Página inicial (Home)
├── config.py               # Constantes globais
├── requirements.txt        # Dependências Python
├── main_cli.py             # Interface de linha de comando
├── .streamlit/
│   ├── config.toml         # Configurações do Streamlit
│   └── secrets.toml        # Credenciais (NÃO versionar com valores reais)
├── pages/
│   ├── 1_Dashboard.py
│   ├── 2_Mapa_de_Rotas.py
│   ├── 3_Analise_por_Veiculo.py
│   ├── 4_Historico.py
│   └── 5_Upload_de_Dados.py
├── core/
│   ├── cache_manager.py    # Orquestra Drive vs. local
│   ├── database.py         # Camada DuckDB (consultas SQL)
│   ├── drive_manager.py    # Integração Google Drive
│   ├── loader.py           # Leitura e limpeza de CSVs
│   ├── processor.py        # Classificação de paradas
│   ├── routes.py           # Agrupamento e análise de rotas
│   ├── analytics.py        # KPIs e resumo diário
│   ├── stats.py            # Estatísticas de velocidade e ignição
│   └── map_builder.py      # Mapas Folium (CLI) e PyDeck (portal)
├── components/
│   ├── filters.py          # Filtros da sidebar
│   ├── charts.py           # Gráficos Plotly
│   └── kpi_cards.py        # Cards de métricas
├── utils/
│   └── helpers.py          # Funções auxiliares
└── data/
    └── uploads/            # CSVs locais (excluídos do Git)
```
