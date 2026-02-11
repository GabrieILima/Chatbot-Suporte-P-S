import logging
import shutil
import re
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.config import API_HOST, API_PORT, DEBUG, RAW_DATA_DIR
from src.rag.generator import RAGGenerator
from src.ingestion.ingest import ingest_file, ingest_directory

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------------------
app = FastAPI(
    title="Chatbot Suporte P&S",
    description="API de um chatbot baseado em RAG",
    version="1.0.0"
)

# ------------------------------------------------------------------------------
# Lazy singletons
# ------------------------------------------------------------------------------
_rag = None
def _get_rag():
    """
    Inicializa o RAGGenerator sob demanda para evitar falha no /health
    quando não há OPENAI_API_KEY. Se o LLM não estiver disponível, o gerador
    entra em fallback (retorna trechos + fontes).
    """
    global _rag
    if _rag is None:
        _rag = RAGGenerator()
    return _rag

# ------------------------------------------------------------------------------
# Pydantic models
# ------------------------------------------------------------------------------
class AskRequest(BaseModel):
    question: str
    k: int = 5
    min_score: float = 0.0

# ------------------------------------------------------------------------------
# Helpers de upload -> alinhar com parse_path_metadata
# ------------------------------------------------------------------------------
_SANITIZE_RE = re.compile(r"[^a-z0-9\-]+")

def _sanitize_title(name: str) -> str:
    """
    Normaliza o título para o padrão de arquivo: minúsculo, hífens, sem acentos/esp. 
    Ex.: "Recebimento de Material" -> "recebimento-de-material"
    """
    n = name.lower().strip().replace(" ", "-")
    n = _SANITIZE_RE.sub("-", n)
    return re.sub(r"-{2,}", "-", n).strip("-")

def _ensure_version(name: str) -> str:
    """
    Garante que o nome contenha sufixo __vYYYY-MM.
    Se não houver, adiciona o mês corrente.
    """
    if "__v" in name:
        return name
    v = datetime.now().strftime("v%Y-%m")
    return f"{name}__{v}"

# ------------------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------------------
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
    Faz uma pergunta ao RAG. Se o LLM estiver indisponível, retorna fallback
    com trechos relevantes.
    """
    try:
        result = _get_rag().generate(
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
    Faz uma pergunta e retorna também as fontes (caminhos dos arquivos).
    """
    try:
        result = _get_rag().generate_with_sources(
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
    Upload de documento compatível com o parser de ingestão.
    - Salva em data/raw/sistemas/_sandbox/
    - Normaliza o nome para titulo__vYYYY-MM.ext
    - Ingestão incremental do arquivo salvo
    """
    allowed = {".pdf", ".docx", ".txt"}
    ext = Path(file.filename).suffix.lower()

    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado. Use: {', '.join(sorted(allowed))}"
        )

    # Garante o caminho: data/raw/sistemas/_sandbox/
    sandbox = Path(RAW_DATA_DIR) / "sistemas" / "_sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)

    # Normaliza o nome do arquivo
    base = Path(file.filename).stem
    title = _sanitize_title(base)
    titlev = _ensure_version(title)
    dst = sandbox / f"{titlev}{ext}"

    # Grava o arquivo
    try:
        with open(dst, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        logger.error(f"Falha ao gravar arquivo: {e}")
        raise HTTPException(status_code=500, detail="Falha ao salvar arquivo")

    # Ingestão incremental do arquivo salvo
    try:
        ok = ingest_file(str(dst), root=str(RAW_DATA_DIR))
    except Exception as e:
        logger.error(f"Falha ao ingerir arquivo '{dst}': {e}")
        raise HTTPException(status_code=500, detail=f"Falha na ingestão: {e}")

    if not ok:
        return {
            "status": "warning",
            "message": "Arquivo salvo, mas não foi ingerido (verifique padrão de pasta/nome).",
            "path": str(dst)
        }

    return {
        "status": "success",
        "message": "Arquivo salvo e ingerido com sucesso.",
        "path": str(dst)
    }

@app.post("/ingest-batch")
async def ingest_batch():
    """
    Ingestão em lote: percorre data/raw, descobre, extrai, chunka e indexa.
    """
    try:
        stats = ingest_directory(str(RAW_DATA_DIR))
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Erro no endpoint /ingest-batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------------------
# Exec local
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG
    )