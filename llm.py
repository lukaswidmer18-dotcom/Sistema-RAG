"""Groq LLM client: builds the grounded prompt and generates contract-audit answers."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from groq import Groq

from pipeline import SearchResult

logger = logging.getLogger(__name__)

load_dotenv()

MODEL_NAME = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "Você é um auditor jurídico especializado em análise de contratos. "
    "Responda EXCLUSIVAMENTE com base nos trechos de CONTEXTO fornecidos, extraídos do "
    "contrato enviado pelo usuário. Regras obrigatórias:\n"
    "1. Se a resposta não estiver explicitamente no CONTEXTO, responda apenas: "
    '"Não foi possível localizar essa informação no documento fornecido."\n'
    "2. NUNCA invente, deduza ou complete informações que não estejam no texto do CONTEXTO.\n"
    "3. Sempre que possível, referencie o número do trecho usado (ex: 'conforme Trecho 2').\n"
    "4. Seja objetivo e direto, em português, no tom de um parecer jurídico executivo."
)


class LLMError(Exception):
    """Raised when the Groq API call fails or returns an unusable response."""


def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise LLMError(
            "GROQ_API_KEY não configurada. Defina a variável de ambiente ou crie um arquivo .env "
            "(veja .env.example)."
        )
    return Groq(api_key=api_key)


def build_context_block(results: list[SearchResult]) -> str:
    """Format retrieved chunks into a numbered context block for the prompt."""
    blocks = [
        f"[Trecho {i} - Fonte: {result['source']}, Bloco #{result['chunk_index']}]\n{result['text']}"
        for i, result in enumerate(results, start=1)
    ]
    return "\n\n".join(blocks)


def ask_question(question: str, context_results: list[SearchResult]) -> str:
    """Generate a grounded answer for `question` using only the retrieved chunks.

    Returns the anti-hallucination fallback message when no context was retrieved,
    without calling the LLM at all.
    """
    if not context_results:
        return "Não foi possível localizar essa informação no documento fornecido."

    client = _get_client()
    context_block = build_context_block(context_results)
    user_message = f"CONTEXTO:\n{context_block}\n\nPERGUNTA: {question}"

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=1024,
        )
    except Exception as exc:
        logger.error("Falha na chamada à API Groq: %s", exc)
        raise LLMError(f"Erro ao consultar o modelo Groq: {exc}") from exc

    answer = response.choices[0].message.content
    if not answer:
        raise LLMError("O modelo Groq retornou uma resposta vazia.")
    return answer.strip()
