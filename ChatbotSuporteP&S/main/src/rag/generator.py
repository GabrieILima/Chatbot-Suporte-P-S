import logging
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from src.config import OPENAI_API_KEY, MODEL_NAME
from src.rag.retriever import Retriever
from src.rag.vectorstore import VectorStore

logger = logging.getLogger(__name__)


class RAGGenerator:
    """Orquestrador do sistema RAG (Retrieval-Augmented Generation)."""
    
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY não configurada")
        
        self.retriever = Retriever(VectorStore())
        self.llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model_name=MODEL_NAME,
            temperature=0.7
        )
        
        self.prompt_template = ChatPromptTemplate.from_template(
            """Você é um assistente de suporte P&S. Use o contexto fornecido para responder à pergunta do usuário.
            
Contexto:
{context}

Pergunta: {question}

Resposta:"""
        )
        
        logger.info("RAGGenerator inicializado")
    
    def generate(self, query: str, k: int = 5, min_score: float = 0.0) -> dict:
        """
        Gera uma resposta baseada em RAG.
        
        Args:
            query: Pergunta do usuário
            k: Número de documentos para recuperar
            min_score: Pontuação mínima de relevância
        
        Returns:
            Dicionário com resposta e contexto utilizado
        """
        try:
            # Recuperar contexto
            context = self.retriever.retrieve_context(query, k=k, min_score=min_score)
            
            # Gerar resposta
            chain = self.prompt_template | self.llm
            response = chain.invoke({
                "context": context,
                "question": query
            })
            
            logger.info(f"Resposta gerada para: {query}")
            
            return {
                "question": query,
                "answer": response.content,
                "context": context,
                "status": "success"
            }
        
        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {str(e)}")
            return {
                "question": query,
                "answer": "Desculpe, ocorreu um erro ao processar sua pergunta.",
                "context": "",
                "status": "error",
                "error": str(e)
            }
    
    def generate_with_sources(self, query: str, k: int = 5) -> dict:
        """
        Gera uma resposta e inclui as fontes utilizadas.
        
        Args:
            query: Pergunta do usuário
            k: Número de documentos para recuperar
        
        Returns:
            Dicionário com resposta, contexto e fontes
        """
        try:
            # Recuperar documentos
            results = self.retriever.retrieve(query, k=k)
            
            if not results:
                return {
                    "question": query,
                    "answer": "Desculpe, não encontrei documentos relevantes para sua pergunta.",
                    "sources": [],
                    "status": "no_results"
                }
            
            # Construir contexto
            context = "\n".join([f"- {r['content'][:200]}..." for r in results])
            
            # Gerar resposta
            chain = self.prompt_template | self.llm
            response = chain.invoke({
                "context": context,
                "question": query
            })
            
            # Extrair fontes
            sources = list({r["metadata"].get("source") for r in results})
            
            return {
                "question": query,
                "answer": response.content,
                "sources": sources,
                "status": "success"
            }
        
        except Exception as e:
            logger.error(f"Erro ao gerar resposta com fontes: {str(e)}")
            return {
                "question": query,
                "answer": "Desculpe, ocorreu um erro ao processar sua pergunta.",
                "sources": [],
                "status": "error",
                "error": str(e)
            }
