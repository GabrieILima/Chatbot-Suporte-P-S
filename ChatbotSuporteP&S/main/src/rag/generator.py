import logging
from typing import List, Tuple, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from src.config import OPENAI_API_KEY, MODEL_NAME
from src.rag.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)

class RAGGenerator:
    def __init__(self):
        self._llm = None
        self._prompt = ChatPromptTemplate.from_template(
            """Você é um assistente de suporte P&S. Use SOMENTE o contexto para responder de forma objetiva.
Se o contexto não contiver a resposta, diga que não encontrou nos manuais.
Responda em português e, quando fizer sentido, em passos numerados.

Contexto:
{context}

Pergunta: {question}

Resposta:"""
        )

    def _get_llm(self):
        if self._llm is None:
            if not OPENAI_API_KEY:
                raise RuntimeError("OPENAI_API_KEY ausente — LLM indisponível.")
            self._llm = ChatOpenAI(
                api_key=OPENAI_API_KEY,
                model_name=MODEL_NAME,
                temperature=0.3
            )
        return self._llm

    def _retrieve(self, query: str, k: int) -> List[Tuple[Any, float]]:
        vs = get_vectorstore()
        return vs.similarity_search_with_score(query, k=k)

    def _build_context(self, hits: List[Tuple[Any, float]], min_score: float = 0.0) -> Tuple[str, List[str]]:
        ctxs, sources = [], []
        for doc, score in hits:
            if score < min_score:
                continue
            ctxs.append(doc.page_content)
            src = doc.metadata.get("source_path", "desconhecido")
            sources.append(src)
        return "\n\n---\n\n".join(ctxs), list(dict.fromkeys(sources))

    def generate(self, query: str, k: int = 5, min_score: float = 0.0) -> dict:
        try:
            hits = self._retrieve(query, k=k)
            context, sources = self._build_context(hits, min_score=min_score)

            if not context.strip():
                return {"question": query, "answer": "Não encontrei informação suficiente nos manuais para responder.", "context": "", "sources": [], "status": "no_context"}

            try:
                llm = self._get_llm()
                chain = self._prompt | llm
                resp = chain.invoke({"context": context, "question": query})
                answer = resp.content
            except Exception as e:
                logger.warning(f"LLM indisponível, usando fallback: {e}")
                answer = "Contexto encontrado, mas o LLM está indisponível. Seguem os trechos relevantes."

            return {"question": query, "answer": answer, "context": context, "sources": sources, "status": "success"}

        except Exception as e:
            logger.error(f"Erro em generate: {e}")
            return {"question": query, "answer": "Erro ao processar a pergunta.", "context": "", "sources": [], "status": "error", "error": str(e)}

    def generate_with_sources(self, query: str, k: int = 5) -> dict:
        try:
            hits = self._retrieve(query, k=k)
            if not hits:
                return {"question": query, "answer": "Não encontrei documentos relevantes para sua pergunta.", "sources": [], "status": "no_results"}

            context, sources = self._build_context(hits, min_score=0.0)

            try:
                llm = self._get_llm()
                chain = self._prompt | llm
                resp = chain.invoke({"context": context, "question": query})
                answer = resp.content
            except Exception as e:
                logger.warning(f"LLM indisponível, usando fallback: {e}")
                answer = "Contexto encontrado, mas o LLM está indisponível. Seguem os trechos relevantes."

            return {"question": query, "answer": answer, "sources": sources, "status": "success"}

        except Exception as e:
            logger.error(f"Erro em generate_with_sources: {e}")
            return {"question": query, "answer": "Erro ao processar a pergunta.", "sources": [], "status": "error", "error": str(e)}