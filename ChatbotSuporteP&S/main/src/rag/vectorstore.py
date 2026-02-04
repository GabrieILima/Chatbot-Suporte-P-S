# -*- coding: utf-8 -*-
"""
Vector store simples baseado em arquivo JSON, com embeddings de verdade.
Compatível com:
- add_documents(List[Document])
- delete(where={"doc_id": ...})
- similarity_search_with_score(query, k) -> List[Tuple[Document, float]]

Mantém persistência em {PERSIST_DIR}/documents.json.
"""

import os
import json
import math
from typing import List, Tuple, Dict, Any

from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings

from src.config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL, OPENAI_API_KEY

_embeddings_singleton = None
_store_singleton = None


def get_embeddings():
    """
    Singleton de embeddings usando HuggingFace (local, sem API).
    Usa 'paraphrase-multilingual-MiniLM-L12-v2' para melhor suporte a português.
    """
    global _embeddings_singleton
    if _embeddings_singleton is None:
        _embeddings_singleton = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            cache_folder=None
        )
    return _embeddings_singleton


class SimpleVectorStore:
    """
    Implementação simples de vector store:
    - Persiste em JSON (page_content, metadata, embedding)
    - Faz similarity search por cosine similarity.
    """

    FILENAME = "documents.json"

    def __init__(self, persist_directory: str):
        self.persist_directory = persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)
        self.filepath = os.path.join(self.persist_directory, self.FILENAME)
        self._emb = get_embeddings()
        self._data: List[Dict[str, Any]] = []
        self._load()


    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = []
        else:
            self._data = []

    def _save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False)



    def delete(self, filter: Dict[str, Any] = None, where: Dict[str, Any] = None):
        """
        Remove documentos que casem com o filtro.
        Aceita 'filter=' ou 'where=' como argumento.
        Ex.: delete(filter={"doc_id": "<sha256:...>"}) remove todos os chunks daquele doc.
        """
        filtro = filter or where
        if not filtro:
            return
        key, val = next(iter(filtro.items()))
        before = len(self._data)
        self._data = [d for d in self._data if d.get("metadata", {}).get(key) != val]
        after = len(self._data)
        # print(f"[SimpleVectorStore] Documentos removidos para {key}: {val} ({before - after} removido[s])")
        self._save()

    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        Gera embeddings e adiciona documentos (chunks).
        Retorna lista de doc_ids (um por chunk, reutilizando metadata.doc_id).
        """
        if not documents:
            return []
        texts = [d.page_content for d in documents]
        vectors = self._emb.embed_documents(texts)

        ids = []
        for d, vec in zip(documents, vectors):
            doc_id = (d.metadata or {}).get("doc_id", "unknown")
            self._data.append({
                "page_content": d.page_content,   
                "metadata": d.metadata or {},
                "embedding": vec
            })
            ids.append(doc_id)

        self._save()
        # print(f"[SimpleVectorStore] {len(ids)} documentos salvos em {self.filepath}")
        return ids

    def persist(self):
        """
        Aqui é no-op porque salvamos a cada operação. Mantido por compatibilidade.
        """
        pass


    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (na * nb)

    def similarity_search_with_score(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        """
        Retorna top-k como [(Document, score)], onde score = cosine_similarity (0-1).
        1.0 = perfeita similaridade, 0.0 = nenhuma similaridade.
        """
        if not self._data:
            return []

        q_vec = self._emb.embed_query(query)
        scored: List[Tuple[Document, float]] = []
        for entry in self._data:
            sim = self._cosine_similarity(q_vec, entry["embedding"])
            doc = Document(
                page_content=entry["page_content"],
                metadata=entry["metadata"],
            )
            scored.append((doc, sim))

        scored.sort(key=lambda t: t[1], reverse=True)  # maior similaridade primeiro
        return scored[:k]


def get_vectorstore():
    """
    Singleton do store simples (mesma assinatura do seu projeto).
    """
    global _store_singleton
    if _store_singleton is None:
        _store_singleton = SimpleVectorStore(CHROMA_PERSIST_DIR)  # ou PERSIST_DIR
    return _store_singleton