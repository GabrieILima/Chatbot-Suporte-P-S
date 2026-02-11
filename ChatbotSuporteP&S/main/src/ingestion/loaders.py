import os
import datetime
import logging
from typing import List, Dict, Iterable, Tuple
import hashlib
import re

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.document_loaders.word_document import Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Extensões permitidas
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx'}

# Prefixos de arquivos a ignorar (temporários / ocultos)
IGNORED_PREF = {'~$', '.'}

def is_ignored_file(filename: str) -> bool:
    for p in IGNORED_PREF:
        if filename.startswith(p):
            return True
    return False

def filter_files(root_dir: str) -> Iterable[str]:
    """Itera recursivamente e retorna caminhos completos de arquivos válidos."""
    for root, _, files in os.walk(root_dir):
        for fn in files:
            if is_ignored_file(fn):
                continue
            yield os.path.join(root, fn)

def discover_files(root_dir: str) -> List[Dict]:
    """
    Descobre arquivos em root_dir e retorna uma lista com:
    - source_path (str)
    - extension   (str)
    - size_bytes  (int)
    - modified_at (str ISO8601)
    """
    results: List[Dict] = []
    if not os.path.exists(root_dir):
        return results

    for path in filter_files(root_dir):   # <— corrigido (era 'ilter_files')
        extension = os.path.splitext(path)[1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            continue
        try:
            stat = os.stat(path)
            size_bytes = int(stat.st_size)
            modified_at = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
        except Exception:
            continue

        results.append({
            "source_path": path,
            "extension": extension,
            "size_bytes": size_bytes,
            "modified_at": modified_at,
        })
    return results

_VERSION_RE = re.compile(r'^v\d{4}-\d{2}(-\d{2})?$')  # vYYYY-MM or vYYYY-MM-DD

def parse_path_metadata(source_path: str, root_dir: str) -> Tuple[Dict, Dict]:
    """
    Extrai metadados a partir de:
      <root_dir>/<category>/<system?>/<title>__<version>.<ext>
    onde category ∈ {processos, sistemas}
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

    name, _ext = os.path.splitext(filename)
    if "__" not in name:
        return {}, {"reason": "missing_version_separator"}

    title, version = name.split("__", 1)

    meta = {
        "category": category,
        "system": system,
        "title": title,
        "version": version
    }

    if not _VERSION_RE.match(version):
        meta["_version_warning"] = "non_standard_version_format"

    return meta, {}

def compute_checksum(source_path: str, algo: str = "sha256", block_size: int = 1 << 20) -> str:
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

def build_document_records(root_dir: str, discovered: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    val: List[Dict] = []
    ign: List[Dict] = []
    for item in discovered:
        source_path = item["source_path"]
        ext = item["extension"]

        meta, err = parse_path_metadata(source_path, root_dir)
        if err:
            ign.append({"source_path": source_path, "reason": err["reason"]})
            continue

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
        if meta.get("_version_warning"):
            rec["_version_warning"] = meta["_version_warning"]
        val.append(rec)

    return val, ign

def extract_text_docs(source_path: str, extension: str):
    ext = extension.lower()
    try:
        if ext == ".pdf":
            return PyPDFLoader(source_path).load()
        elif ext == ".docx":
            return Docx2txtLoader(source_path).load()
        elif ext == ".txt":
            return TextLoader(source_path, encoding="utf-8").load()
        else:
            raise ValueError(f"Extensão não suportada: {ext}")
    except Exception as e:
        logger.exception("Erro ao carregar arquivo para extração: %s", source_path)
        return []

def _normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    while "\n\n" in t:
        t = t.replace("\n\n", "\n")
    return t.strip()

def chunk_document(docs, chunk_size: int = 1000, chunk_overlap: int = 200):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    for d in docs:
        d.page_content = _normalize_text(d.page_content)
    return splitter.split_documents(docs)

def build_chunks_for_record(record: dict, chunk_size: int = 1000, chunk_overlap: int = 200):
    source_path = record["source_path"]
    extension = record["extension"]
    docs = extract_text_docs(source_path, extension)
    if not docs:
        logger.warning("Nenhum documento extraído de %s", source_path)
        return []
    chunks = chunk_document(docs, chunk_size, chunk_overlap)
    logger.info("Chunks gerados para %s: %d", source_path, len(chunks))
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
