"""RAG core: load docs, chunk, embed with Chroma, generate with Sonnet 4.6."""
import os
import uuid
from pathlib import Path

import chromadb
from anthropic import Anthropic
from dotenv import load_dotenv
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

load_dotenv()

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

_client: Anthropic | None = None
_embedder: SentenceTransformer | None = None
_chroma = None
_collection = None


def get_anthropic() -> Anthropic:
    global _client
    if _client is None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        _client = Anthropic()
    return _client


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def get_collection():
    global _chroma, _collection
    if _collection is None:
        Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
        _chroma = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = _chroma.get_or_create_collection(
            name="docs", metadata={"hnsw:space": "cosine"}
        )
    return _collection


def read_document(path: str) -> str:
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        reader = PdfReader(str(p))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    # .txt / .md / others treated as utf-8 text
    return p.read_text(encoding="utf-8", errors="ignore")


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return [c for c in (c.strip() for c in chunks) if c]


def ingest_text(text: str, doc_id: str, filename: str) -> int:
    chunks = chunk_text(text)
    if not chunks:
        return 0
    col = get_collection()
    embedder = get_embedder()
    embeddings = embedder.encode(chunks, show_progress_bar=False).tolist()
    ids = [f"{doc_id}_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]
    col.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=[{"doc_id": doc_id, "filename": filename, "chunk": i} for i in range(len(chunks))],
    )
    return len(chunks)


def ingest_file(saved_path: str, filename: str, doc_id: str | None = None) -> dict:
    doc_id = doc_id or f"{Path(filename).stem}_{uuid.uuid4().hex[:8]}"
    text = read_document(saved_path)
    n = ingest_text(text, doc_id, filename)
    return {"doc_id": doc_id, "filename": filename, "chunks": n, "chars": len(text)}


SYSTEM_PROMPT = (
    "You are a helpful RAG assistant. Answer the user's question using ONLY the provided context. "
    "If the answer is not in the context, say you don't know. Cite sources like [filename chunk N] when relevant."
)


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    col = get_collection()
    embedder = get_embedder()
    q_emb = embedder.encode([query], show_progress_bar=False).tolist()
    res = col.query(query_embeddings=q_emb, n_results=top_k)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    out = []
    for d, m in zip(docs, metas):
        out.append({"text": d, "filename": (m or {}).get("filename", "?"), "chunk": (m or {}).get("chunk", 0)})
    return out


def answer(query: str, top_k: int = 5, max_tokens: int = 1024) -> dict:
    ctx = retrieve(query, top_k)
    context_block = "\n\n---\n\n".join(
        f"[{c['filename']} chunk {c['chunk']}]\n{c['text']}" for c in ctx
    ) or "(no retrieved context)"
    user_msg = f"Context:\n{context_block}\n\nQuestion: {query}"
    resp = get_anthropic().messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return {"answer": text, "model": ANTHROPIC_MODEL, "sources": ctx}
