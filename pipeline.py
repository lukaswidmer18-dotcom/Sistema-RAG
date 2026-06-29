"""RAG pipeline: PDF extraction, intelligent chunking, ChromaDB indexing and semantic search."""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import BinaryIO, TypedDict

import chromadb
from fastembed import TextEmbedding
from pypdf import PdfReader

logger = logging.getLogger(__name__)

CHROMA_PERSIST_DIR = str(Path(__file__).parent / "chroma_db")
COLLECTION_NAME = "contract_audit"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K_DEFAULT = 5

# Multilingual retrieval-tuned model. Plain sentence-similarity models (e.g. MiniLM) ranked the
# correct clause outside the top 10 for natural Portuguese questions in testing; e5 models are
# trained specifically for asymmetric query/passage retrieval and require the "query: "/
# "passage: " prefixes below to perform as benchmarked.
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-large"

CLAUSE_HEADER_PATTERN = re.compile(
    r"(?=^\s*(?:CL[ÁA]USULA|ARTIGO|SE[ÇC][ÃA]O)\s+[\dA-ZÀ-Ú]+)",
    re.IGNORECASE | re.MULTILINE,
)


class SearchResult(TypedDict):
    text: str
    source: str
    chunk_index: int
    distance: float


class PipelineError(Exception):
    """Raised when PDF extraction, chunking or indexing fails."""


def extract_text_from_pdf(file: BinaryIO) -> str:
    """Extract raw text from a PDF file-like object (e.g. Streamlit UploadedFile)."""
    try:
        reader = PdfReader(file)
    except Exception as exc:
        raise PipelineError(f"Não foi possível ler o PDF: {exc}") from exc

    pages_text: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            pages_text.append(page.extract_text() or "")
        except Exception as exc:
            logger.warning("Falha ao extrair texto da página %s: %s", page_number, exc)

    full_text = "\n".join(pages_text).strip()
    if not full_text:
        raise PipelineError(
            "O PDF não contém texto extraível (pode ser um documento escaneado sem OCR)."
        )
    return full_text


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text first by clause header (CLÁUSULA/ARTIGO/SEÇÃO) so unrelated clauses never
    share a chunk and dilute each other's embedding, then by a size-bounded sliding window
    within each clause, snapping each boundary to the nearest paragraph/sentence/space so a
    single clause is not cut mid-way."""
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap deve ser menor que chunk_size")

    text = text.strip()
    if not text:
        return []

    sections = [s.strip() for s in CLAUSE_HEADER_PATTERN.split(text) if s.strip()]
    if len(sections) <= 1:
        return _window_chunk(text, chunk_size, chunk_overlap)

    chunks: list[str] = []
    for section in sections:
        chunks.extend(_window_chunk(section, chunk_size, chunk_overlap))
    return chunks


def _window_chunk(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Slide a size-bounded window over `text`, snapping each boundary to the nearest
    paragraph/sentence/space so a single clause is not cut mid-way."""
    chunks: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        if end < text_length:
            end = _snap_to_boundary(text, start, end)

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break
        next_start = end - chunk_overlap
        start = next_start if next_start > start else end

    return chunks


def _snap_to_boundary(text: str, start: int, end: int) -> int:
    """Search backward from `end` for the nearest paragraph/sentence/space break."""
    window = text[start:end]
    for separator in ("\n\n", "\n", ". ", " "):
        idx = window.rfind(separator)
        if idx > 0:
            return start + idx + len(separator)
    return end


class ContractAuditPipeline:
    """Wraps a persistent local ChromaDB collection holding the audited contract."""

    def __init__(self, persist_directory: str = CHROMA_PERSIST_DIR) -> None:
        self._client = chromadb.PersistentClient(path=persist_directory)
        self._embedding_model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)
        self._collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        # Embeddings are always supplied explicitly (see _embed_*), so no embedding_function
        # is registered here: e5 needs different "query: "/"passage: " prefixes for queries vs.
        # documents, which Chroma's single embedding_function callback cannot distinguish.
        return self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def _embed_documents(self, texts: list[str]) -> list[list[float]]:
        prefixed = [f"passage: {text}" for text in texts]
        return [vector.tolist() for vector in self._embedding_model.embed(prefixed)]

    def _embed_query(self, text: str) -> list[float]:
        embeddings = list(self._embedding_model.embed([f"query: {text}"]))
        return embeddings[0].tolist()

    def reset(self) -> None:
        """Drop and recreate the collection so a newly uploaded contract starts clean."""
        try:
            self._client.delete_collection(COLLECTION_NAME)
        except Exception as exc:
            logger.debug("Coleção anterior não encontrada para remoção: %s", exc)
        self._collection = self._get_or_create_collection()

    def index_pdf(self, file: BinaryIO, source_name: str) -> int:
        """Extract, chunk and index a PDF. Returns the number of chunks indexed."""
        text = extract_text_from_pdf(file)
        chunks = chunk_text(text)
        if not chunks:
            raise PipelineError("Nenhum bloco de texto foi gerado a partir do PDF.")

        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [{"source": source_name, "chunk_index": i} for i in range(len(chunks))]
        embeddings = self._embed_documents(chunks)

        self._collection.add(ids=ids, documents=chunks, metadatas=metadatas, embeddings=embeddings)
        return len(chunks)

    def search(self, query: str, top_k: int = TOP_K_DEFAULT) -> list[SearchResult]:
        """Return the top_k most relevant indexed chunks for the given query."""
        if not query.strip():
            raise ValueError("A pergunta não pode estar vazia.")

        if self._collection.count() == 0:
            return []

        query_embedding = self._embed_query(query)
        results = self._collection.query(query_embeddings=[query_embedding], n_results=top_k)

        documents = results.get("documents") or [[]]
        metadatas = results.get("metadatas") or [[]]
        distances = results.get("distances") or [[]]

        search_results: list[SearchResult] = []
        for doc, meta, distance in zip(documents[0], metadatas[0], distances[0]):
            search_results.append(
                SearchResult(
                    text=doc,
                    source=str(meta.get("source", "desconhecido")),
                    chunk_index=int(meta.get("chunk_index", -1)),
                    distance=float(distance),
                )
            )
        return search_results
