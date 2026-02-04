import logging
from typing import List
from src.rag.vectorstore import VectorStore
from src.utils import logger as base_logger

logger = logging.getLogger(__name__)


class Retriever:
    """Recuperador de documentos com busca semântica e filtros."""
    
    def __init__(self, vectorstore: VectorStore = None):
        self.vectorstore = vectorstore or VectorStore()
    
    def retrieve(self, query: str, k: int = 5, min_score: float = 0.0) -> List[dict]:
        """
        Recupera documentos relevantes para a consulta.
        
        Args:
            query: Texto da consulta
            k: Número máximo de documentos a retornar
            min_score: Pontuação mínima de relevância (0-1)
        
        Returns:
            Lista de documentos com metadados
        """
        try:
            results = self.vectorstore.search_with_scores(query, k=k)
            
            # Filtrar por score mínimo
            filtered_results = [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                }
                for doc, score in results
                if score >= min_score
            ]
            
            logger.info(f"Recuperados {len(filtered_results)} documentos para: {query}")
            return filtered_results
        
        except Exception as e:
            logger.error(f"Erro ao recuperar documentos: {str(e)}")
            return []
    
    def retrieve_context(self, query: str, k: int = 5, min_score: float = 0.0) -> str:
        """
        Recupera documentos e retorna como string de contexto.
        
        Args:
            query: Texto da consulta
            k: Número máximo de documentos a retornar
            min_score: Pontuação mínima de relevância
        
        Returns:
            String formatada com os documentos recuperados
        """
        results = self.retrieve(query, k=k, min_score=min_score)
        
        if not results:
            return "Nenhum documento relevante encontrado."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result["metadata"].get("source", "Desconhecido")
            page = result["metadata"].get("page", "N/A")
            score = result["score"]
            content = result["content"][:500]  # Primeiros 500 caracteres
            
            context_parts.append(
                f"[{i}] Fonte: {source} (página {page}, relevância: {score:.2f})\n"
                f"{content}...\n"
            )
        
        return "\n".join(context_parts)
