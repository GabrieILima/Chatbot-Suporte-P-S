from pathlib import Path

from langchain_core.documents import Document

from src.ingestion import ingest


def test_ingest_file_success(monkeypatch, tmp_path: Path):
    root = tmp_path / "raw"
    fpath = root / "sistemas" / "_sandbox" / "guia__v2026-02.txt"
    fpath.parent.mkdir(parents=True)
    fpath.write_text("conteudo de teste", encoding="utf-8")

    calls = {"reindex": 0}

    def fake_build_chunks_for_record(record, chunk_size, chunk_overlap):
        return [Document(page_content="chunk", metadata={})]

    def fake_reindex(doc_id, chunks):
        calls["reindex"] += 1
        assert doc_id.startswith("sha256:")
        assert len(chunks) == 1
        return 1

    monkeypatch.setattr(ingest, "build_chunks_for_record", fake_build_chunks_for_record)
    monkeypatch.setattr(ingest, "_reindex_document_chunks", fake_reindex)

    ok = ingest.ingest_file(str(fpath), root=str(root))

    assert ok is True
    assert calls["reindex"] == 1
