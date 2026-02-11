# -*- coding: utf-8 -*-
import os
import json
import math
from typing import List, Tuple, Dict, Any

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from src.config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL

_embeddings_singleton = None
_store_singleton = None


def get_embeddings():
    global _embeddings_singleton
    if _embeddings_singleton is None:
        _embeddings_singleton = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            cache_folder=None,
        )
    return _embeddings_singleton


class SimpleVectorStore:
    FILENAME = "documents.json"

    def __init__(self, persist_directory: str | os.PathLike):
        self.persist_directory = str(persist_directory)
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
        filtro = filter or where
        if not filtro:
            return
        key, val = next(iter(filtro.items()))
        self._data = [d for d in self._data if d.get("metadata", {}).get(key) != val]
        self._save()

    def add_documents(self, documents: List[Document]) -> List[str]:
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
                "embedding": vec,
            })
            ids.append(doc_id)

        self._save()
        return ids

    def persist(self):
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
        if not self._data:
            return []
        q_vec = self._emb.embed_query(query)
        scored: List[Tuple[Document, float]] = []
        for entry in self._data:
            sim = self._cosine_similarity(q_vec, entry["embedding"])
            doc = Document(page_content=entry["page_content"], metadata=entry["metadata"])
            scored.append((doc, sim))
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:k]


def get_vectorstore():
    global _store_singleton
    if _store_singleton is None:
        _store_singleton = SimpleVectorStore(CHROMA_PERSIST_DIR)
    return _store_singleton
