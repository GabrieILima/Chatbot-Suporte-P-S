# Chatbot de Suporte P&S

Um chatbot baseado em RAG (Retrieval-Augmented Generation) para atender questoes sobre produtos e servicos.

## Recursos

- Ingestao de documentos (PDF, DOCX, TXT)
- Busca semantica com embeddings
- Integracao com LLM via OpenAI
- API FastAPI para requisicoes
- Containerizacao com Docker

## Estrutura do Projeto

```text
chatbot/
|-- data/                    # Dados brutos e vetores persistidos
|-- src/
|   |-- config.py           # Configuracoes centralizadas
|   |-- utils.py            # Funcoes auxiliares
|   |-- ingestion/          # Pipeline de ingestao de documentos
|   |-- rag/                # Logica de RAG
|   `-- api/                # API FastAPI
|-- requirements.txt        # Dependencias de runtime
|-- requirements-dev.txt    # Dependencias de desenvolvimento/scripts
|-- docker-compose.yml      # Orquestracao Docker
`-- README.md               # Este arquivo
```

## Instalacao

### Pre-requisitos

- Python 3.11.x (recomendado)
- Docker (opcional)

### Configuracao Local

1. Clone o repositorio:
```bash
git clone <repo-url>
cd chatbot
```

2. Garanta o Python 3.11 (o projeto inclui `.python-version`):
```bash
python --version
```

3. Crie e ative o ambiente virtual:
```bash
python -m venv .venv
```

4. Crie arquivo `.env` a partir do exemplo:
```bash
cp .env.example .env
```

5. Configure as variaveis de ambiente (especialmente `OPENAI_API_KEY`).

6. Instale dependencias de runtime:
```bash
pip install -r requirements.txt
```

7. (Opcional) Instale dependencias de desenvolvimento/scripts:
```bash
pip install -r requirements-dev.txt
```

8. Execute a API:
```bash
uvicorn src.api.main:app --reload
```

### Com Docker

O `Dockerfile` instala apenas dependencias de runtime (`requirements.txt`).

```bash
docker-compose up --build
```

## Uso

### Endpoints da API

- **POST /ask** - Fazer pergunta ao chatbot
- **POST /upload** - Enviar documento para ingestao
- **GET /health** - Verificar status da API

## Desenvolvimento

Para adicionar novos documentos:
1. Coloque os arquivos em `data/raw/`
2. Execute `python -m src.ingestion.ingest`

## Licenca

Proprietary
