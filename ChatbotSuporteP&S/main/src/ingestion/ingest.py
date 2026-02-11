from typing import List, Tuple, Dict
from langchain_core.documents import Document

from src.config import RAW_DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from src.rag.vectorstore import get_vectorstore
from src.ingestion.loaders import (
    discover_files,
    build_document_records,
    build_chunks_for_record
)

def _reindex_document_chunks(doc_id: str, chunks: List[Document]) -> int:
    """Reindexa os chunks de um documento no vectorstore."""
    vs = get_vectorstore()
    try:
        vs.delete(filter={"doc_id": doc_id})
    except Exception:
        pass
    if not chunks:
        return 0
    vs.add_documents(chunks)
    vs.persist()
    return len(chunks)

def ingest_directory(root: str = str(RAW_DATA_DIR)) -> Dict:
    """Ingestão em lote a partir de root (ex.: ./data/raw)."""
    base = discover_files(root)
    validos, ignorados = build_document_records(root, base)

    total_chunks = 0
    total_docs = 0
    for rec in validos:
        chunks = build_chunks_for_record(rec, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        n = _reindex_document_chunks(rec["doc_id"], chunks)
        total_chunks += n
        total_docs += 1

    return {
        "root": root,
        "processed_docs": total_docs,
        "indexed_chunks": total_chunks,
        "ignored": ignorados
    }

def ingest_file(path: str, root: str = str(RAW_DATA_DIR)) -> bool:
    """Ingestão de um único arquivo (após upload)."""
    import os, datetime
    ext = os.path.splitext(path)[1].lower()
    discovered = [{
        "source_path": path,
        "extension": ext,
        "size_bytes": int(os.stat(path).st_size),
        "modified_at": datetime.datetime.fromtimestamp(os.stat(path).st_mtime).isoformat()
    }]

    validos, ignorados = build_document_records(root, discovered)
    if not validos:
        # opcional: logar ignorados
        return False

    rec = validos[0]
    chunks = build_chunks_for_record(rec, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    _reindex_document_chunks(rec["doc_id"], chunks)
    return True

# Modo de teste manual
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingestão de documentos para RAG")
    parser.add_argument("--mode", choices=["discover", "index"], default="discover")
    args = parser.parse_args()

    if args.mode == "discover":
        base = discover_files(RAW_DATA_DIR)
        validos, ignorados = build_document_records(RAW_DATA_DIR, base)
        print(f"[Descoberta] válidos={len(validos)} ignorados={len(ignorados)}")
        for rec in validos[:5]:
            chunks = build_chunks_for_record(rec, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
            print(f"- {rec['title']} ({rec['version']}) → {len(chunks)} chunk(s)")
    else:
        stats = ingest_directory(str(RAW_DATA_DIR))
        print("[Resumo]", stats)