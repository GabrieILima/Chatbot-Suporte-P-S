from pathlib import Path

import pytest

from src.ingestion.loaders import discover_files, parse_path_metadata


def test_parse_path_metadata_valid_sistemas(tmp_path: Path):
    root = tmp_path / "raw"
    fpath = root / "sistemas" / "erp" / "manual__v2026-02.txt"
    fpath.parent.mkdir(parents=True)
    fpath.write_text("conteudo", encoding="utf-8")

    meta, err = parse_path_metadata(str(fpath), str(root))

    assert err == {}
    assert meta["category"] == "sistemas"
    assert meta["system"] == "erp"
    assert meta["title"] == "manual"
    assert meta["version"] == "v2026-02"


def test_parse_path_metadata_invalid_category(tmp_path: Path):
    root = tmp_path / "raw"
    fpath = root / "outra" / "arquivo__v2026-02.txt"
    fpath.parent.mkdir(parents=True)
    fpath.write_text("conteudo", encoding="utf-8")

    with pytest.raises(ValueError):
        parse_path_metadata(str(fpath), str(root))


def test_discover_files_filters_extensions_and_ignored(tmp_path: Path):
    root = tmp_path / "raw"
    valid = root / "processos" / "doc__v2026-02.txt"
    hidden = root / "processos" / ".oculto.txt"
    temp = root / "processos" / "~$temp.docx"
    unsupported = root / "processos" / "nota.md"

    valid.parent.mkdir(parents=True)
    valid.write_text("ok", encoding="utf-8")
    hidden.write_text("ignore", encoding="utf-8")
    temp.write_text("ignore", encoding="utf-8")
    unsupported.write_text("ignore", encoding="utf-8")

    files = discover_files(str(root))
    paths = {item["source_path"] for item in files}

    assert str(valid) in paths
    assert str(hidden) not in paths
    assert str(temp) not in paths
    assert str(unsupported) not in paths
