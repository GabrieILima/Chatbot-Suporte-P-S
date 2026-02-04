import os
from pathlib import Path

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
