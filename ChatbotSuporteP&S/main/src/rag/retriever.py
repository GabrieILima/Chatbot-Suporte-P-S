import logging
from typing import List, Dict
from src.rag.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)

class Retriever:
    """Recuperador usando o SimpleVectorStore (maior similaridade = melhor)."""

    def __init__(self):
        self.vs = get_vectorstore()

    def retrieve(self, query: str, k: int = 5, min_score: float = 0.0) -> List[Dict]:
        try:
            results = self.vs.similarity_search_with_score(query, k=k)
            out = []
            for doc, score in results:
                if score < min_score:
                    continue
                out.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                })
            logger.info(f"Recuperados {len(out)} documentos para: {query}")
            return out
        except Exception as e:
            logger.error(f"Erro ao recuperar documentos: {e}")
            return []

    def retrieve_context(self, query: str, k: int = 5, min_score: float = 0.0) -> str:
        results = self.retrieve(query, k=k, min_score=min_score)
        if not results:
            return "Nenhum documento relevante encontrado."
        parts = []
        for i, r in enumerate(results, 1):
            source = r["metadata"].get("source_path", "desconhecido")
            score = r["score"]
            content = r["content"][:500].replace("\n", " ")
            parts.append(f"[{i}] Fonte: {source} (relevância: {score:.2f})\n{content}...\n")
        return "\n".join(parts)