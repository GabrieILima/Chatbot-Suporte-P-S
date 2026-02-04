import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Diretório raiz do projeto
BASE_DIR = Path(__file__).parent.parent

# Diretório de dados brutos
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

# Diretório de dados processados (Chroma)
CHROMA_DIR = BASE_DIR / "data" / "chroma"

# Cria os diretórios se não existirem
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# Extensões de arquivo suportadas
SUPPORTED_EXTENSIONS = {
    '.pdf', '.txt', '.docx', '.xlsx', '.csv', 
    '.json', '.md', '.html', '.xml', '.pptx'
}

# Configurações de chunking para RAG
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Configurações de embeddings e vectorstore
# Diretório de persistência do Chroma
CHROMA_PERSIST_DIR = BASE_DIR / "data" / "chroma"

# Modelo de embeddings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Chave da OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Nome do modelo LLM
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHROMA_PERSIST_DIR = CHROMA_DIR

# Configurações de OpenAI e LLM
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = "gpt-3.5-turbo"
