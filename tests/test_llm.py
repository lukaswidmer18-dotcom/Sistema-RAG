"""Tests for llm.py: context formatting and the anti-hallucination guard."""

from __future__ import annotations

import os

import pytest

import llm
from pipeline import SearchResult

SAMPLE_RESULTS: list[SearchResult] = [
    {
        "text": "Em caso de rescisao antecipada, sera devida multa de 20% do valor remanescente.",
        "source": "contrato.pdf",
        "chunk_index": 6,
        "distance": 0.12,
    },
    {
        "text": "O contrato vigorara por 12 meses a partir da assinatura.",
        "source": "contrato.pdf",
        "chunk_index": 3,
        "distance": 0.15,
    },
]


class TestBuildContextBlock:
    def test_numbers_each_chunk_and_includes_source_metadata(self) -> None:
        block = llm.build_context_block(SAMPLE_RESULTS)
        assert "[Trecho 1 - Fonte: contrato.pdf, Bloco #6]" in block
        assert "[Trecho 2 - Fonte: contrato.pdf, Bloco #3]" in block
        assert "multa de 20%" in block

    def test_empty_results_produce_empty_block(self) -> None:
        assert llm.build_context_block([]) == ""


class TestAskQuestion:
    def test_returns_fallback_without_calling_api_when_no_context(self, monkeypatch) -> None:
        def _fail_if_called(*args, **kwargs):
            raise AssertionError("Groq client should not be constructed with no context")

        monkeypatch.setattr(llm, "_get_client", _fail_if_called)

        answer = llm.ask_question("Qual o valor da multa?", [])
        assert answer == "Não foi possível localizar essa informação no documento fornecido."

    def test_raises_llm_error_when_api_key_missing(self, monkeypatch) -> None:
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        with pytest.raises(llm.LLMError):
            llm.ask_question("Qual o valor da multa?", SAMPLE_RESULTS)


@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY not set")
class TestAskQuestionLive:
    """Hits the real Groq API. Skipped automatically when no key is configured."""

    def test_grounded_answer_cites_the_retrieved_clause(self) -> None:
        answer = llm.ask_question("Qual a multa por rescisao antecipada?", SAMPLE_RESULTS)
        assert "20%" in answer

    def test_refuses_to_answer_outside_retrieved_context(self) -> None:
        answer = llm.ask_question("Qual o nome do CEO da empresa contratante?", SAMPLE_RESULTS)
        assert "não foi possível localizar" in answer.lower() or "não encontr" in answer.lower()
