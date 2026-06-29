"""Tests for pipeline.py: PDF extraction, clause-aware chunking, ChromaDB index/search."""

from __future__ import annotations

import io

import pytest

import pipeline as p


class TestChunkText:
    def test_empty_text_returns_no_chunks(self) -> None:
        assert p.chunk_text("   ") == []

    def test_overlap_must_be_smaller_than_chunk_size(self) -> None:
        with pytest.raises(ValueError):
            p.chunk_text("x", chunk_size=100, chunk_overlap=100)

    def test_short_text_returns_single_chunk(self) -> None:
        text = "Texto curto sem cabecalho de clausula."
        chunks = p.chunk_text(text)
        assert chunks == [text]

    def test_no_chunk_exceeds_chunk_size(self) -> None:
        text = "Lorem ipsum dolor sit amet consectetur adipiscing elit. " * 200
        chunks = p.chunk_text(text, chunk_size=1000, chunk_overlap=200)
        assert all(len(c) <= 1000 for c in chunks)
        assert len(chunks) > 1

    def test_consecutive_chunks_overlap(self) -> None:
        text = "Lorem ipsum dolor sit amet consectetur adipiscing elit. " * 200
        chunks = p.chunk_text(text, chunk_size=1000, chunk_overlap=200)
        # the tail of chunk[i] and the head of chunk[i+1] should share text
        # (boundary snapping means the overlap isn't always exactly 200 chars)
        for a, b in zip(chunks, chunks[1:]):
            tail = a[-50:]
            assert tail[-20:] in b[: len(tail) + 50]

    def test_no_degenerate_tiny_chunks_around_paragraph_break(self) -> None:
        """Regression test: a paragraph break inside the sliding window used to make `start`
        creep forward 1 char at a time while `end` stayed pinned to the same boundary,
        producing hundreds of near-empty chunks instead of advancing past it."""
        clause_a = "CLAUSULA 1. Disposicoes gerais sobre o objeto do contrato. " * 40
        clause_b = "CLAUSULA 2. Penalidades, multas e rescisao antecipada. " * 40
        text = clause_a + "\n\n" + clause_b

        chunks = p._window_chunk(text, chunk_size=1000, chunk_overlap=200)

        assert len(chunks) < 20, "chunking degenerated into many tiny fragments"
        assert all(len(c) > 50 for c in chunks[:-1]), "found a degenerate tiny chunk"

    def test_splits_by_clause_header_before_windowing(self, sample_contract_text: str) -> None:
        chunks = p.chunk_text(sample_contract_text)

        vigencia_chunks = [c for c in chunks if "PRAZO DE VIGENCIA" in c.upper()]
        assert len(vigencia_chunks) == 1
        vigencia_chunk = vigencia_chunks[0]

        # the vigência clause must not be merged with the unrelated execution-regime clause
        assert "REGIME DE EXECUCAO" not in vigencia_chunk.upper()
        normalized = " ".join(vigencia_chunk.split())
        assert "01 de agosto de 2026" in normalized

    def test_falls_back_to_plain_window_without_clause_headers(self) -> None:
        text = "Paragrafo um sem cabecalho.\n\nParagrafo dois tambem sem cabecalho de clausula."
        chunks = p.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_recognizes_artigo_and_secao_headers(self) -> None:
        text = (
            "Preambulo do documento.\n\n"
            "ARTIGO 1 - Definicoes gerais aplicaveis a este instrumento.\n\n"
            "SECAO 2 - Disposicoes finais e foro de eleicao."
        )
        chunks = p.chunk_text(text)
        assert any(c.upper().startswith("ARTIGO 1") for c in chunks)
        assert any(c.upper().startswith("SECAO 2") for c in chunks)


class TestExtractTextFromPdf:
    def test_extracts_text_from_real_pdf(self, sample_pdf_path) -> None:
        with open(sample_pdf_path, "rb") as f:
            text = p.extract_text_from_pdf(f)
        assert "multa" in text.lower()
        assert "rescis" in text.lower()

    def test_raises_pipeline_error_on_garbage_bytes(self) -> None:
        with pytest.raises(p.PipelineError):
            p.extract_text_from_pdf(io.BytesIO(b"not a real pdf"))


class TestContractAuditPipeline:
    def test_index_and_search_round_trip(
        self, monkeypatch, temp_chroma_dir, sample_contract_text
    ) -> None:
        monkeypatch.setattr(p, "extract_text_from_pdf", lambda file: sample_contract_text)

        pipe = p.ContractAuditPipeline(persist_directory=temp_chroma_dir)
        chunk_count = pipe.index_pdf(file=None, source_name="contrato_teste.pdf")
        assert chunk_count > 0

        results = pipe.search("Quando o contrato ira acabar?", top_k=3)
        assert len(results) > 0
        assert results[0]["source"] == "contrato_teste.pdf"
        # the clause-aware chunking + multilingual embedding combo (see DESIGN decisions in
        # README) must surface the vigência clause for this question, not an unrelated one
        assert "vigencia" in results[0]["text"].lower() or "2026" in results[0]["text"]

    def test_search_on_empty_collection_returns_no_results(self, temp_chroma_dir) -> None:
        pipe = p.ContractAuditPipeline(persist_directory=temp_chroma_dir)
        assert pipe.search("qualquer pergunta") == []

    def test_search_rejects_empty_query(self, temp_chroma_dir) -> None:
        pipe = p.ContractAuditPipeline(persist_directory=temp_chroma_dir)
        with pytest.raises(ValueError):
            pipe.search("   ")

    def test_reset_clears_previously_indexed_document(
        self, monkeypatch, temp_chroma_dir, sample_contract_text
    ) -> None:
        monkeypatch.setattr(p, "extract_text_from_pdf", lambda file: sample_contract_text)

        pipe = p.ContractAuditPipeline(persist_directory=temp_chroma_dir)
        pipe.index_pdf(file=None, source_name="contrato_teste.pdf")
        assert pipe._collection.count() > 0

        pipe.reset()
        assert pipe._collection.count() == 0
        assert pipe.search("qualquer pergunta") == []

    def test_index_pdf_rejects_pdf_with_no_extractable_text(
        self, monkeypatch, temp_chroma_dir
    ) -> None:
        monkeypatch.setattr(p, "extract_text_from_pdf", lambda file: "")
        pipe = p.ContractAuditPipeline(persist_directory=temp_chroma_dir)
        with pytest.raises(p.PipelineError):
            pipe.index_pdf(file=None, source_name="vazio.pdf")
