import os
import datetime
from typing import List, Dict, Iterable, Tuple
import hashlib
import re
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.document_loaders.word_document import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document




# Regra de extensões permitidas na biblioteca
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx'}

# Nomes e prefixos que indicam arquivo temporário(à serem ignorados)
IGNORED_PREF = {'~$', '.'}

def is_ignored_file(filename: str) -> bool:
    """Verifica se o arquivo deve ser ignorado com base no nome."""
    for p in IGNORED_PREF:
        if filename.startswith(p):
            return True
    return False

def filter_files(root_dir: str)-> Iterable[str]:
    """Gera uma lista de arquivos válidos na árvore de diretórios.
"""
    for root, _, files in os.walk(root_dir):
        for fn in files:
            if is_ignored_file(fn):
                continue
            yield os.path.join(root, fn)


def discover_files(root_dir: str) -> list[Dict]:
    """Descobre arquivos válidos na árvore de diretórios.
    
        Retorna: lista de dicts com chaves:
        - source_path (str)
        - extension   (str)
        - size_bytes  (int)
        - modified_at (str ISO8601)
        """
    results: list[Dict] = []
    
    if not os.path.exists(root_dir):
        # Se a pasta não existir, retornamos vazio
        return results

    for path in ilter_files(root_dir):
        extension = os.path.splitext(path)[1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            continue

        print("Arquivo encontrado:", path)

        try:
            stat = os.stat(path)
            size_bytes = int(stat.st_size)
            modified_at = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
        except Exception:
                # Ignorar arquivos que não podem ser acessados
            print("Não foi possível acessar o arquivo:", path)
            continue
        
        results.append({
            "source_path": path,
            "extension": extension,
            "size_bytes": size_bytes,
            "modified_at": modified_at,
        })

    return results

_VERSION_RE = re.compile(r'^v\d{4}-\d{2}(-\d{2})?$') #vYYYY-MM or vYYYY-MM-DD
def parse_path_metadata(source_path: str, root_dir: str) -> Tuple[Dict, Dict]:
    """Extrai metadados do caminho do arquivo.
    
    Retorna dois dicionários:
    - metadados extraídos
    - partes do caminho (path parts)

    Regras:
    -Espera -se que o source_path esteja dentro do root_dir/category/subcategory/...
    -category pertence{"processos", "sistemas"}
    -Se for sistemas, espera-se uma subcategoria (nome do sistema)
    -Nome do arquivo: title__version.ext
    """
    norm_root = os.path.normpath(root_dir)
    norm_path = os.path.normpath(source_path)

    try:
        rel = os.path.relpath(norm_path, norm_root)
    except ValueError:
        raise ValueError(f"O arquivo '{source_path}' não está dentro do diretório raiz '{root_dir}'")
    parts = rel.split(os.sep)
    if len(parts) < 2:
        raise ValueError(f"Caminho relativo '{rel}' muito curto para extrair metadados.")
    category = parts[0]
    if category not in {"processos", "sistemas"}:
        raise ValueError(f"Categoria inválida '{category}' no caminho '{rel}'.")
    
    system = None
    filename = None

    if category == "sistemas":
        if len(parts) < 3:
            raise ValueError(f"Caminho relativo '{rel}' muito curto para extrair sistema.")
        system = parts[1]
        filename = parts[2]
    else:
        filename = parts[1]
    # separa <title>__<version>.<ext>
    name, _ext = os.path.splitext(filename)
    if "__" not in name:
        return {}, {"reason": "missing_version_separator"}

    title, version = name.split("__", 1)

    meta = {
        "category": category,
        "system": system,          # pode ser None em 'processos'
        "title": title,
        "version": version
    }

    # Pequena validação de versão (não bloqueia; só informa)
    if not _VERSION_RE.match(version):
        # Você pode decidir no futuro transformar isso em erro.
        meta["_version_warning"] = "non_standard_version_format"

    return meta, {}

# ----------  CHECKSUM (SHA-256)  ----------

def compute_checksum(source_path: str, algo: str = "sha256", block_size: int = 1 << 20) -> str:
    """
    Calcula o hash do arquivo (padrão SHA-256) e retorna como string com prefixo 'sha256:'.
    """
    if algo != "sha256":
        raise ValueError("Only sha256 is supported in this version.")

    h = hashlib.sha256()
    with open(source_path, "rb") as f:
        while True:
            chunk = f.read(block_size)
            if not chunk:
                break
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"

# ----------  BUILDER (DISCOVERY + METADATA + CHECKSUM)  ----------

def build_document_records(root_dir: str, discovered: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Dado o resultado do discover_files (lista de dicts básicos),
    enriquece com metadados (category/system/title/version) e checksum (doc_id).

    Retorna (validos, ignorados).
    - validos: lista de dicts completos
    - ignorados: lista de dicts com {"source_path", "reason"} explicando o porquê
    """
    val: List[Dict] = []
    ign: List[Dict] = []

    for item in discovered:
        source_path = item["source_path"]
        ext = item["extension"]

        meta, err = parse_path_metadata(source_path, root_dir)
        if err:
            ign.append({"source_path": source_path, "reason": err["reason"]})
            continue

        # gera checksum como doc_id
        try:
            doc_id = compute_checksum(source_path)
        except Exception as e:
            ign.append({"source_path": source_path, "reason": f"checksum_error: {e}"})
            continue

        rec = {
            "doc_id": doc_id,
            "source_path": source_path,
            "category": meta["category"],
            "system": meta["system"],
            "title": meta["title"],
            "version": meta["version"],
            "extension": ext,
            "size_bytes": item["size_bytes"],
            "modified_at": item["modified_at"]
        }
        # opcional: carregar aviso de versão não padrão
        if meta.get("_version_warning"):
            rec["_version_warning"] = meta["_version_warning"]

        val.append(rec)

    return val, ign

def extract_text_docs(source_path: str, extention: str):
    """Extrai texto de documentos com base na extensão do arquivo."""
    ext = extention.lower()

    try:
        if ext == ".pdf":
            loader = PyPDFLoader(source_path)
            return loader.load()
        elif ext == ".docx":
            loader = Docx2txtLoader(source_path)
            return loader.load()
        elif ext == ".txt":
            loader = TextLoader(source_path, encoding="utf-8")
            return loader.load()
        else:
            raise ValueError(f"Extensão não suportada: {ext}")

    except Exception as e:
        print(f"Erro ao carregar {source_path}: {e}")
        return []
    
def _normalize_text(text: str) -> str:
    """Normaliza o texto removendo espaços extras e linhas em branco."""
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    while "\n\n" in t:
        t = t.replace("\n\n", "\n")
    return t.strip()

def chunk_document(docs, chunk_size: int = 1000, chunk_overlap: int = 200):
    """Divide documentos em pedaços menores usando RecursiveCharacterTextSplitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )

    for d in docs:
        d.page_content = _normalize_text(d.page_content)
    return splitter.split_documents(docs)

def build_chunks_for_record(record: dict, chunk_size: int = 1000, chunk_overlap: int = 200):
    """Constrói pedaços de texto para um registro de documento."""
    source_path = record["source_path"]
    extention = record["extension"]

    docs = extract_text_docs(source_path, extention)
    if not docs:
        print(f"[Aviso] Nenhum documento extraído de {source_path}.")
        return []
    chunks = chunk_document(docs, chunk_size, chunk_overlap)
    print(f"[Chunks] {len(chunks)} pedaço(s) gerado(s) para {source_path}.")
    for c in chunks:
        c.metadata.update({
            "doc_id": record["doc_id"],
            "source_path": source_path,
            "category": record["category"],
            "system": record["system"],
            "title": record["title"],
            "version": record["version"],
        })
    return chunks
    
    