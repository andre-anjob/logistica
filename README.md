# Portal Logístico — Rastreamento de Frota

Esse portal nasceu de uma necessidade real: acompanhar onde a frota está, quanto está rodando, onde para e por quanto tempo — tudo num lugar só, acessível de qualquer computador.

Ele lê os CSVs de rastreamento GPS, processa e guarda tudo num banco DuckDB, e entrega dashboards, mapas e análises de forma rápida. Os arquivos ficam salvos no Google Drive, então os dados persistem mesmo quando o servidor reinicia.

---

## O que você vai encontrar aqui

**Dashboard** — uma visão geral da frota com km rodados, ranking de alertas de velocidade, evolução diária e heatmap de atividade por hora.

**Mapa de Rotas** — o mapa mais útil do portal. Você escolhe um dia e um veículo e vê a rota colorida por velocidade (verde normal, amarelo atenção, vermelho excesso). Ao passar o mouse sobre a linha, aparece a velocidade exata naquele ponto. Círculos azuis marcam paradas, laranjas indicam onde o veículo ficou parado com ignição desligada — útil para identificar riscos de desvio. Amarelos mostram onde o motor ficou ligado parado, desperdiçando combustível.

**Análise por Veículo** — mergulha nos dados de um veículo específico: KPIs, gráficos diários, tabela detalhada e exportação para Excel.

**Histórico** — compara dois períodos lado a lado. Bom para ver se o comportamento da frota melhorou ou piorou.

**Upload de Dados** — onde você envia os CSVs. O portal valida tudo antes de salvar.

---

## Rodando localmente

Você vai precisar de Python 3.11+ e Git instalados.

```bash
git clone https://github.com/SEU_USUARIO/logistica.git
cd logistica
python -m venv .venv
```

Ative o ambiente virtual:

```powershell
# Windows
.\.venv\Scripts\Activate.ps1
```
```bash
# Linux / macOS
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Suba o portal:

```bash
streamlit run app.py
```

Acesse em `http://localhost:8501`. Se você ainda não conectou o Google Drive, tudo bem — o portal funciona normalmente em modo local, salvando os CSVs em `data/uploads/`.

---

## Conectando ao Google Drive

Essa etapa permite que os dados sobrevivam ao reinício do servidor e fiquem acessíveis de qualquer máquina. São cerca de 10 minutos de configuração.

### 1. Criar o projeto no Google Cloud

Entre em [console.cloud.google.com](https://console.cloud.google.com), crie um projeto novo (pode chamar de `painel-logistico`) e ative a **Google Drive API** em *APIs e serviços → Biblioteca*.

### 2. Criar a conta de serviço

Vá em *IAM e administrador → Contas de serviço → Criar conta de serviço*. Dê um nome como `portal-frota` e finalize. Não precisa atribuir nenhum papel.

Depois clique na conta criada, vá na aba **Chaves** e crie uma chave no formato **JSON**. Um arquivo será baixado — guarde ele bem, ele não pode ser recuperado depois.

### 3. Compartilhar a pasta do Drive

Crie uma pasta no Google Drive para guardar os CSVs da frota. Clique com o botão direito nela → **Compartilhar** → cole o e-mail que aparece no campo `client_email` do JSON baixado → defina como **Editor**.

O ID da pasta está na URL quando você abre ela:
`drive.google.com/drive/folders/`**`ESTE_TRECHO_É_O_ID`**

### 4. Preencher o secrets.toml

Abra `.streamlit/secrets.toml`, descomente a seção `[google_drive]` e preencha com os valores do JSON:

```toml
[google_drive]
type             = "service_account"
project_id       = "painel-logistico"
private_key_id   = "valor do JSON"
private_key      = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email     = "portal-frota@painel-logistico.iam.gserviceaccount.com"
client_id        = "valor do JSON"
auth_uri         = "https://accounts.google.com/o/oauth2/auth"
token_uri        = "https://oauth2.googleapis.com/token"
folder_id        = "ID_DA_PASTA_DO_DRIVE"
```

> ⚠️ O `private_key` deve ser copiado exatamente como está no JSON, com os `\n` literais — o portal converte automaticamente.
>
> ⚠️ Nunca suba esse arquivo com valores reais pro Git. O `.gitignore` já o exclui por padrão.

---

## Publicando no Streamlit Community Cloud

Primeiro garanta que o código está no GitHub:

```bash
git add .
git commit -m "versão inicial"
git push origin main
```

Depois:

1. Acesse [share.streamlit.io](https://share.streamlit.io) e conecte sua conta GitHub
2. Clique em **New app** → selecione o repositório → branch `main` → arquivo `app.py`
3. Antes de clicar em Deploy, abra **Advanced settings → Secrets** e cole o conteúdo do seu `secrets.toml` com os valores reais
4. Deploy!

Em 2 ou 3 minutos o portal estará no ar com uma URL pública. Quando você fizer `git push` no futuro, o Streamlit Cloud detecta e atualiza automaticamente.

---

## Adicionando novos dados

A forma mais fácil é pelo próprio portal: acesse **Upload de Dados**, arraste os CSVs e pronto. O portal valida as colunas, descarta coordenadas inválidas e já deixa os dados disponíveis nas outras páginas.

O arquivo precisa ter essas colunas (separador vírgula ou ponto-e-vírgula):

```
Veículo, Placa, Organização, Data da Coordenada, Data da Gravação,
Velocidade, Ignição, Serial, Posição
```

A coluna `Posição` deve vir no formato `latitude,longitude` — por exemplo: `"-3.789100,-38.512300"`. Datas no padrão brasileiro: `dd/mm/aaaa HH:MM:SS`.

---

## Estrutura do projeto

```
├── app.py                  # Página inicial
├── config.py               # Configurações globais
├── requirements.txt        # Dependências
├── .streamlit/
│   ├── config.toml         # Configurações do Streamlit
│   └── secrets.toml        # Credenciais (não versionar com valores reais)
├── pages/                  # As 5 páginas do portal
├── core/
│   ├── cache_manager.py    # Decide entre Drive e modo local
│   ├── database.py         # Consultas SQL via DuckDB
│   ├── drive_manager.py    # Integração com o Google Drive
│   ├── loader.py           # Leitura e limpeza dos CSVs
│   ├── processor.py        # Detecção de paradas
│   ├── routes.py           # Análise de rotas por veículo/dia
│   ├── analytics.py        # KPIs e resumos
│   ├── stats.py            # Estatísticas de velocidade e ignição
│   └── map_builder.py      # Mapas (Folium para CLI, PyDeck para o portal)
├── components/             # Gráficos, filtros e cards reutilizáveis
├── utils/                  # Funções auxiliares
└── data/uploads/           # CSVs locais (excluídos do Git)
```
