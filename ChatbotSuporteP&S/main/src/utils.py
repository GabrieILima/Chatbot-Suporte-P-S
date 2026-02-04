import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_directory_exists(path: str) -> Path:
    """Garante que um diretório existe, criando-o se necessário."""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_file_paths(directory: str, extensions: list) -> list:
    """
    Retorna lista de arquivos em um diretório com extensões específicas.
    
    Args:
        directory: Caminho do diretório
        extensions: Lista de extensões (ex: ['.pdf', '.docx', '.txt'])
    
    Returns:
        Lista de caminhos de arquivos
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        logger.warning(f"Diretório não encontrado: {directory}")
        return []
    
    files = []
    for ext in extensions:
        files.extend(dir_path.glob(f"*{ext}"))
    return files
