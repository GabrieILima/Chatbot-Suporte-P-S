from langchain_core.documents import Document

import src.rag.generator as generator_module
from src.rag.generator import RAGGenerator


def test_generate_fallback_when_llm_unavailable(monkeypatch):
    monkeypatch.setattr(generator_module, "OPENAI_API_KEY", "")
    gen = RAGGenerator()

    hits = [(Document(page_content="conteudo relevante", metadata={"source_path": "doc.txt"}), 0.91)]
    monkeypatch.setattr(gen, "_retrieve", lambda query, k: hits)

    result = gen.generate("pergunta de teste", k=1, min_score=0.0)

    assert result["status"] == "success"
    assert "LLM" in result["answer"]
    assert "Resumo do contexto" in result["answer"]
    assert "conteudo relevante" in result["answer"]
    assert result["sources"] == ["doc.txt"]
