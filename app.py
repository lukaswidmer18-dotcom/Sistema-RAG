"""Streamlit executive dashboard for AI-assisted contract auditing (RAG over a local PDF)."""

from __future__ import annotations

import streamlit as st

from llm import LLMError, ask_question
from pipeline import ContractAuditPipeline, PipelineError, SearchResult

AUDIT_QUESTIONS: list[str] = [
    "Quais são as multas e penalidades previstas em caso de rescisão contratual?",
    "Qual é o prazo de vigência do contrato e quais as condições para renovação?",
    "Existem cláusulas de confidencialidade ou de não-concorrência? Quais são seus termos?",
    "Quais são as condições de pagamento e os critérios de reajuste de valores?",
]

st.set_page_config(
    page_title="Auditoria de Contratos | RAG",
    page_icon="📑",
    layout="wide",
)

# Visual language adapted from Mastercard's design system (see DESIGN.md): warm cream
# canvas instead of white, ink-black pill CTAs, large-radius soft-spread shadows, uppercase
# eyebrow labels with an accent dot instead of decorative emoji. MarkForMC is proprietary;
# Inter is used as the open-source substitute the source design system itself recommends.
_DESIGN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.stApp, .stApp *:not([data-testid="stIconMaterial"]) {
    font-family: 'Inter', 'SofiaSans', Arial, sans-serif !important;
}

.stApp {
    background-color: #F3F0EE;
}

[data-testid="stSidebar"] {
    background-color: #FCFBFA;
    border-right: 1px solid #E8E2DA;
}

h1, h2, h3 {
    color: #141413 !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
}

h1 {
    font-size: 3.4rem !important;
    line-height: 1.05 !important;
}

.eyebrow {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #696969;
    margin: 4px 0;
}
.eyebrow::before {
    content: "";
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: #CF4500;
    flex-shrink: 0;
}

[data-testid="stBaseButton-primary"] {
    background-color: #141413 !important;
    color: #F3F0EE !important;
    border: 1.5px solid #141413 !important;
    border-radius: 20px !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
    padding: 10px 28px !important;
    box-shadow: none !important;
}
[data-testid="stBaseButton-primary"]:hover {
    background-color: #262627 !important;
    border-color: #262627 !important;
    color: #F3F0EE !important;
}
[data-testid="stBaseButton-primary"]:disabled {
    background-color: #D1CDC7 !important;
    border-color: #D1CDC7 !important;
    color: #FCFBFA !important;
}

[data-testid="stBaseButton-secondary"] {
    background-color: #FFFFFF !important;
    color: #141413 !important;
    border: 1.5px solid #141413 !important;
    border-radius: 20px !important;
    font-weight: 500 !important;
    padding: 10px 28px !important;
}

[class*="st-key-audit-card"] {
    background-color: #FCFBFA;
    border-radius: 24px !important;
    border: 1px solid rgba(20, 20, 19, 0.05) !important;
    box-shadow: rgba(0, 0, 0, 0.10) 0px 24px 48px 0px;
    padding: 8px;
}

.stat-strip {
    display: flex;
    gap: 48px;
    margin: 8px 0 4px 0;
}
.stat-strip .stat + .stat {
    border-left: 1px solid #E8E2DA;
    padding-left: 48px;
}
.stat-label {
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 12px;
    font-weight: 700;
    color: #696969;
    margin-bottom: 4px;
}
.stat-value {
    font-size: 2.4rem;
    font-weight: 600;
    color: #141413;
    letter-spacing: -0.02em;
    line-height: 1.1;
    max-width: 320px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

[data-testid="stExpander"] {
    background-color: #FCFBFA;
    border-radius: 16px;
    border: 1px solid #E8E2DA;
}

[data-testid="stChatMessage"] {
    background-color: #FCFBFA;
    border-radius: 24px;
    box-shadow: rgba(0, 0, 0, 0.04) 0px 4px 24px 0px;
}

[data-testid="stChatInput"] {
    border-radius: 999px !important;
    border: 1.5px solid #141413 !important;
    background-color: #FFFFFF !important;
    overflow: hidden;
}
[data-testid="stChatInputSubmitButton"] {
    border-radius: 50% !important;
    background-color: #141413 !important;
}

hr {
    border-color: #E8E2DA;
}

a {
    color: #3860BE;
}
</style>
"""
st.markdown(_DESIGN_CSS, unsafe_allow_html=True)


def _eyebrow(label: str) -> None:
    st.markdown(f'<div class="eyebrow">{label}</div>', unsafe_allow_html=True)


def _stat_strip(stats: list[tuple[str, str]]) -> None:
    items = "".join(
        f'<div class="stat"><div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div></div>'
        for label, value in stats
    )
    st.markdown(f'<div class="stat-strip">{items}</div>', unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_pipeline() -> ContractAuditPipeline:
    return ContractAuditPipeline()


def _init_session_state() -> None:
    st.session_state.setdefault("indexed_file_id", None)
    st.session_state.setdefault("indexed_filename", None)
    st.session_state.setdefault("indexed_chunk_count", 0)
    st.session_state.setdefault("chat_history", [])
    st.session_state.setdefault("audit_results", [])


def _render_sources(results: list[SearchResult]) -> None:
    with st.expander("Fontes utilizadas pela IA"):
        if not results:
            st.caption("Nenhum trecho relevante foi recuperado do documento.")
            return
        for i, result in enumerate(results, start=1):
            st.markdown(
                f"**Trecho {i}** — *{result['source']}*, bloco #{result['chunk_index']} "
                f"(distância: {result['distance']:.4f})"
            )
            st.text(result["text"])
            st.divider()


def _answer(pipeline: ContractAuditPipeline, question: str) -> tuple[str, list[SearchResult]]:
    results = pipeline.search(question)
    answer = ask_question(question, results)
    return answer, results


def _render_sidebar(pipeline: ContractAuditPipeline) -> None:
    with st.sidebar:
        _eyebrow("Documento")
        st.subheader("Contrato em auditoria")
        uploaded_file = st.file_uploader("Envie o contrato (PDF)", type=["pdf"])

        if uploaded_file is None:
            return

        file_id = f"{uploaded_file.name}:{uploaded_file.size}"
        if file_id == st.session_state["indexed_file_id"]:
            st.success(f"'{uploaded_file.name}' já indexado ({st.session_state['indexed_chunk_count']} blocos).")
            return

        with st.spinner("Indexando documento no ChromaDB..."):
            try:
                pipeline.reset()
                chunk_count = pipeline.index_pdf(uploaded_file, uploaded_file.name)
            except PipelineError as exc:
                st.error(f"Falha ao indexar o documento: {exc}")
                return

        st.session_state["indexed_file_id"] = file_id
        st.session_state["indexed_filename"] = uploaded_file.name
        st.session_state["indexed_chunk_count"] = chunk_count
        st.session_state["chat_history"] = []
        st.session_state["audit_results"] = []
        st.success(f"Documento indexado com sucesso ({chunk_count} blocos).")


def _render_header() -> None:
    _eyebrow("Auditoria de contratos")
    st.title("Plataforma de Auditoria de Contratos")
    st.caption("RAG local (ChromaDB) + Groq (Llama 3 70B) — respostas restritas ao conteúdo do contrato enviado.")

    document_label = st.session_state["indexed_filename"] or "Nenhum"
    status = "Pronto" if st.session_state["indexed_filename"] else "Aguardando upload"
    _stat_strip(
        [
            ("Documento", document_label),
            ("Blocos indexados", str(st.session_state["indexed_chunk_count"])),
            ("Status", status),
        ]
    )
    st.divider()


def _render_express_audit(pipeline: ContractAuditPipeline) -> None:
    _eyebrow("Verificação rápida")
    st.subheader("Auditoria Expressa")
    is_ready = st.session_state["indexed_filename"] is not None

    if st.button("Executar Auditoria Expressa", disabled=not is_ready, type="primary"):
        results_by_question = []
        with st.spinner("Executando as 4 perguntas críticas de auditoria..."):
            for question in AUDIT_QUESTIONS:
                try:
                    answer, sources = _answer(pipeline, question)
                except LLMError as exc:
                    answer, sources = f"Erro ao gerar resposta: {exc}", []
                results_by_question.append((question, answer, sources))
        st.session_state["audit_results"] = results_by_question

    if not is_ready:
        st.info("Envie um contrato em PDF na barra lateral para habilitar a Auditoria Expressa.")

    if st.session_state["audit_results"]:
        cols = st.columns(2)
        for i, (question, answer, sources) in enumerate(st.session_state["audit_results"]):
            with cols[i % 2].container(border=True, key=f"audit-card-{i}"):
                st.markdown(f"**{i + 1}. {question}**")
                st.write(answer)
                _render_sources(sources)

    st.divider()


def _render_chat(pipeline: ContractAuditPipeline) -> None:
    _eyebrow("Perguntas livres")
    st.subheader("Pergunte ao Auditor IA")
    is_ready = st.session_state["indexed_filename"] is not None

    for entry in st.session_state["chat_history"]:
        with st.chat_message("user"):
            st.write(entry["question"])
        with st.chat_message("assistant"):
            st.write(entry["answer"])
            _render_sources(entry["sources"])

    question = st.chat_input(
        "Digite sua pergunta sobre o contrato..." if is_ready else "Envie um contrato primeiro",
        disabled=not is_ready,
    )
    if not question:
        return

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Consultando o documento e gerando resposta..."):
            try:
                answer, sources = _answer(pipeline, question)
            except LLMError as exc:
                answer, sources = f"Erro ao gerar resposta: {exc}", []
        st.write(answer)
        _render_sources(sources)

    st.session_state["chat_history"].append(
        {"question": question, "answer": answer, "sources": sources}
    )


def main() -> None:
    _init_session_state()
    pipeline = get_pipeline()

    _render_sidebar(pipeline)
    _render_header()
    _render_express_audit(pipeline)
    _render_chat(pipeline)


if __name__ == "__main__":
    main()
