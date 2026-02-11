import logging
from typing import List, Tuple, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import OPENAI_API_KEY, MODEL_NAME
from src.rag.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)


class RAGGenerator:
    def __init__(self):
        self._llm = None
        self._prompt = ChatPromptTemplate.from_template(
            """Voce e um assistente de suporte P&S. Use SOMENTE o contexto para responder de forma objetiva.
Se o contexto nao contiver a resposta, diga que nao encontrou nos manuais.
Responda em portugues e, quando fizer sentido, em passos numerados.

Contexto:
{context}

Pergunta: {question}

Resposta:"""
        )

    def _get_llm(self):
        if self._llm is None:
            if not OPENAI_API_KEY:
                raise RuntimeError("OPENAI_API_KEY ausente - LLM indisponivel.")
            self._llm = ChatOpenAI(
                api_key=OPENAI_API_KEY,
                model_name=MODEL_NAME,
                temperature=0.3,
            )
        return self._llm

    def _retrieve(self, query: str, k: int) -> List[Tuple[Any, float]]:
        vs = get_vectorstore()
        return vs.similarity_search_with_score(query, k=k)

    def _build_context(
        self, hits: List[Tuple[Any, float]], min_score: float = 0.0
    ) -> Tuple[str, List[str]]:
        ctxs, sources = [], []
        for doc, score in hits:
            if score < min_score:
                continue
            ctxs.append(doc.page_content)
            src = doc.metadata.get("source_path", "desconhecido")
            sources.append(src)
        return "\n\n---\n\n".join(ctxs), list(dict.fromkeys(sources))

    def _fallback_answer(self, context: str) -> str:
        """Retorna fallback com resumo curto do contexto quando o LLM falha."""
        snippets = []
        for chunk in context.split("\n\n---\n\n"):
            text = chunk.strip().replace("\n", " ")
            if text:
                snippets.append(text[:180])
            if len(snippets) >= 2:
                break

        if not snippets:
            return "Contexto encontrado, mas o LLM esta indisponivel."

        lines = ["Contexto encontrado, mas o LLM esta indisponivel. Resumo do contexto:"]
        for i, snippet in enumerate(snippets, 1):
            lines.append(f"{i}. {snippet}...")
        return "\n".join(lines)

    def generate(self, query: str, k: int = 5, min_score: float = 0.0) -> dict:
        try:
            hits = self._retrieve(query, k=k)
            context, sources = self._build_context(hits, min_score=min_score)

            if not context.strip():
                return {
                    "question": query,
                    "answer": "Nao encontrei informacao suficiente nos manuais para responder.",
                    "context": "",
                    "sources": [],
                    "status": "no_context",
                }

            try:
                llm = self._get_llm()
                chain = self._prompt | llm
                resp = chain.invoke({"context": context, "question": query})
                answer = resp.content
            except Exception as e:
                logger.warning(f"LLM indisponivel, usando fallback: {e}")
                answer = self._fallback_answer(context)

            return {
                "question": query,
                "answer": answer,
                "context": context,
                "sources": sources,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Erro em generate: {e}")
            return {
                "question": query,
                "answer": "Erro ao processar a pergunta.",
                "context": "",
                "sources": [],
                "status": "error",
                "error": str(e),
            }

    def generate_with_sources(self, query: str, k: int = 5) -> dict:
        try:
            hits = self._retrieve(query, k=k)
            if not hits:
                return {
                    "question": query,
                    "answer": "Nao encontrei documentos relevantes para sua pergunta.",
                    "sources": [],
                    "status": "no_results",
                }

            context, sources = self._build_context(hits, min_score=0.0)

            try:
                llm = self._get_llm()
                chain = self._prompt | llm
                resp = chain.invoke({"context": context, "question": query})
                answer = resp.content
            except Exception as e:
                logger.warning(f"LLM indisponivel, usando fallback: {e}")
                answer = self._fallback_answer(context)

            return {
                "question": query,
                "answer": answer,
                "sources": sources,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Erro em generate_with_sources: {e}")
            return {
                "question": query,
                "answer": "Erro ao processar a pergunta.",
                "sources": [],
                "status": "error",
                "error": str(e),
            }
