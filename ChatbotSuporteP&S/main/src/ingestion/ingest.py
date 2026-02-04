from src.config import RAW_DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from typing import List
from langchain_core.documents import Document
from src.rag.vectorstore import get_vectorstore
from src.ingestion.loaders import (
    discover_files,
    build_document_records,
    build_chunks_for_record
)


def reindex_document_chunks(doc_id: str, chunks: List[Document]) -> int:
    """Reindexa os chunks de um documento específico no vectorstore."""
    vectorstore = get_vectorstore()
    try:
        # Remover chunks antigos do documento
        vectorstore.delete(filter={"doc_id": doc_id})
        # print(f"[Reindexação] Chunks antigos removidos para doc_id: {doc_id}")
    except Exception as e:
        print(f"[Erro] Falha ao remover chunks antigos para doc_id: {doc_id}: {e}")

    if not chunks:
        # print(f"[Reindexação] Nenhum chunk para adicionar para doc_id: {doc_id}")
        return 0
    
    vectorstore.add_documents(chunks)
    vectorstore.persist()
    # print(f"[Reindexação] {len(chunks)} novos chunk(s) adicionados para doc_id: {doc_id}")
    return len(chunks)


def main_index_test():
    """Teste de indexação: descobre, chunka e indexa no vectorstore."""
    base = discover_files(RAW_DATA_DIR)
    # print(f"[Descoberta] {len(base)} arquivo(s) candidatos em {RAW_DATA_DIR}.")

    validos, ignorados = build_document_records(RAW_DATA_DIR, base)
    # print(f"[Metadados] Válidos: {len(validos)} | Ignorados: {len(ignorados)}\n")
    
    if ignorados:
        pass  # Oculta detalhes de ignorados
    
    if not validos:
        print("[INFO] Nenhum documento válido para processar.")
        return
    
    total_chunks = 0
    for rec in validos:
        chunks = build_chunks_for_record(
            rec,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        # print(f"- {rec['title']} ({rec['version']}) → {len(chunks)} chunk(s)")
        
        n = reindex_document_chunks(rec['doc_id'], chunks)
        # print(f"  Reindexados: {n} chunk(s)")
        total_chunks += n

    print(f"[Resumo] Total de chunks reindexados: {total_chunks}")

    if total_chunks > 0:
        pass  # Oculta teste de similaridade
    else:
        print("[INFO] Nenhum chunk reindexado para testar a busca por similaridade.")




def main_discovery_records_and_chunks():
    """Teste de descoberta: apenas lista os arquivos e gera chunks (sem indexação)."""
    # 1) Descoberta básica
    base = discover_files(RAW_DATA_DIR)
    # print(f"[Descoberta] {len(base)} arquivo(s) candidatos em {RAW_DATA_DIR}.")

    # 2) Metadados + checksum
    validos, ignorados = build_document_records(RAW_DATA_DIR, base)
    # print(f"[Metadados] Válidos: {len(validos)} | Ignorados: {len(ignorados)}\n")

    if ignorados:
        pass  # Oculta detalhes de ignorados

    if not validos:
        print("[INFO] Nenhum documento válido para processar.")
        return

    # 3) Para cada documento válido, gerar chunks
    total_chunks = 0
    for rec in validos:
        chunks = build_chunks_for_record(
            rec,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        print(f"- {rec['title']} ({rec['version']}) → {len(chunks)} chunk(s)")
        # Exibe uma amostra do primeiro chunk
        if chunks:
            preview = chunks[0].page_content[:300].replace("\n", " ")
            print(f"  Exemplo primeiro chunk: {preview}...")
        total_chunks += len(chunks)

    print(f"\n[Resumo] Total de chunks gerados: {total_chunks}")


def reindex_document_chunks(doc_id: str, chunks: List[Document]) -> int:
    """Reindexa os chunks de um documento específico no vectorstore."""
    vectorstore = get_vectorstore()
    try:
    # Remover chunks antigos do documento
        vectorstore.delete(filter={"doc_id": doc_id})
        print(f"[Reindexação] Chunks antigos removidos para doc_id: {doc_id}")
    except Exception as e:
        print(f"[Erro] Falha ao remover chunks antigos para doc_id: {doc_id}: {e}")
        pass

    if not chunks:
        print(f"[Reindexação] Nenhum chunk para adicionar para doc_id: {doc_id}")
        return 0
    
    vectorstore.add_documents(chunks)
    print(f"[Reindexação] {len(chunks)} novos chunk(s) adicionados para doc_id: {doc_id}")
    vectorstore.persist()
    return len(chunks)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sistema de ingestão de documentos para RAG")
    parser.add_argument(
        "--mode",
        choices=["discover", "index"],
        default="discover",
        help="'discover': apenas lista e chunka | 'index': descobre, chunka e indexa"
    )
    args = parser.parse_args()
    
    if args.mode == "discover":
        main_discovery_records_and_chunks()
    elif args.mode == "index":
        main_index_test()