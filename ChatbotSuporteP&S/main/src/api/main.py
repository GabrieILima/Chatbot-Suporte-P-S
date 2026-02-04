import logging
import shutil
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.config import API_HOST, API_PORT, DEBUG
from src.rag.generator import RAGGenerator
from src.ingestion.ingest import IngestPipeline
from src.utils import ensure_directory_exists

logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="Chatbot Suporte P&S",
    description="API de um chatbot baseado em RAG",
    version="1.0.0"
)

# Inicializar componentes
rag_generator = RAGGenerator()
ingest_pipeline = IngestPipeline()


# Modelos Pydantic
class AskRequest(BaseModel):
    question: str
    k: int = 5
    min_score: float = 0.0


class AskResponse(BaseModel):
    question: str
    answer: str
    context: str = ""
    status: str


# Endpoints
@app.get("/health")
async def health():
    """Verifica o status da API."""
    return {
        "status": "healthy",
        "service": "Chatbot Suporte P&S",
        "version": "1.0.0"
    }


@app.post("/ask")
async def ask(request: AskRequest):
    """
    Endpoint para fazer perguntas ao chatbot.
    
    Args:
        request: Objeto com pergunta e parâmetros
    
    Returns:
        Resposta gerada pelo modelo RAG
    """
    try:
        result = rag_generator.generate(
            query=request.question,
            k=request.k,
            min_score=request.min_score
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Erro no endpoint /ask: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask-with-sources")
async def ask_with_sources(request: AskRequest):
    """
    Endpoint para fazer perguntas e retornar as fontes utilizadas.
    
    Args:
        request: Objeto com pergunta e parâmetros
    
    Returns:
        Resposta com fontes
    """
    try:
        result = rag_generator.generate_with_sources(
            query=request.question,
            k=request.k
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Erro no endpoint /ask-with-sources: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Endpoint para upload de documentos para ingestão.
    
    Args:
        file: Arquivo para fazer upload
    
    Returns:
        Status do upload e ingestão
    """
    try:
        # Validar extensão
        allowed_extensions = ['.pdf', '.docx', '.txt']
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Formato não suportado. Use: {', '.join(allowed_extensions)}"
            )
        
        # Salvar arquivo
        upload_dir = ensure_directory_exists("./data/raw")
        file_path = upload_dir / file.filename
        
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Ingerir arquivo
        success = ingest_pipeline.ingest_file(str(file_path))
        
        if success:
            return {
                "status": "success",
                "message": f"Documento '{file.filename}' carregado e processado com sucesso",
                "file": file.filename
            }
        else:
            return {
                "status": "error",
                "message": f"Erro ao processar o documento '{file.filename}'",
                "file": file.filename
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint /upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest-batch")
async def ingest_batch():
    """
    Endpoint para ingestão em lote de documentos de ./data/raw
    
    Returns:
        Estatísticas da ingestão
    """
    try:
        stats = ingest_pipeline.ingest_directory("./data/raw")
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Erro no endpoint /ingest-batch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG
    )
