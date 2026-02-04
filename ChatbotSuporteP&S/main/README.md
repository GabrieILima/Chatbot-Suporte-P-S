# Chatbot de Suporte P&S

Um chatbot baseado em RAG (Retrieval-Augmented Generation) para atender questões sobre produtos e serviços.

## Recursos

- Ingestão de documentos (PDF, DOCX, TXT)
- Busca semântica com Chroma
- Integração com LLM via OpenAI
- API FastAPI para requisições
- Containerização com Docker

## Estrutura do Projeto

```
chatbot/
├── data/                    # Dados brutos e vetores persistidos
├── src/
│   ├── config.py           # Configurações centralizadas
│   ├── utils.py            # Funções auxiliares
│   ├── ingestion/          # Pipeline de ingestão de documentos
│   ├── rag/                # Lógica de RAG
│   └── api/                # API FastAPI
├── requirements.txt        # Dependências Python
├── docker-compose.yml      # Orquestração Docker
└── README.md               # Este arquivo
```

## Instalação

### Pré-requisitos

- Python 3.11+
- Docker (opcional)

### Configuração Local

1. Clone o repositório:
```bash
git clone <repo-url>
cd chatbot
```

2. Crie arquivo `.env` a partir do exemplo:
```bash
cp .env.example .env
```

3. Configure as variáveis de ambiente (especialmente `OPENAI_API_KEY`)

4. Instale as dependências:
```bash
pip install -r requirements.txt
```

5. Execute a API:
```bash
uvicorn src.api.main:app --reload
```

### Com Docker

```bash
docker-compose up --build
```

## Uso

### Endpoints da API

- **POST /ask** - Fazer pergunta ao chatbot
- **POST /upload** - Enviar documento para ingestão
- **GET /health** - Verificar status da API

## Desenvolvimento

Para adicionar novos documentos:
1. Coloque os arquivos em `data/raw/`
2. Execute `python -m src.ingestion.ingest`

## Licença

Proprietary
