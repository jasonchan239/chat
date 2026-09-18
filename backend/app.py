"""FastAPI server for RAG chatbot (Sonnet 4.6 + Chroma)."""
import shutil
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag import answer, get_collection, ingest_file

load_dotenv()

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED = {".pdf", ".txt", ".md"}

app = FastAPI(title="RAG Chatbot (Sonnet 4.6)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    top_k: int = 5


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(400, f"Unsupported type {suffix}. Use PDF, TXT, or MD.")
    doc_id = f"{Path(file.filename).stem}_{uuid.uuid4().hex[:8]}"
    saved = UPLOAD_DIR / f"{doc_id}{suffix}"
    with saved.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        result = ingest_file(str(saved), file.filename or saved.name, doc_id)
    except Exception as e:
        raise HTTPException(500, f"Ingest failed: {e}")
    return result


@app.post("/chat")
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(400, "message is empty")
    try:
        return answer(req.message, top_k=req.top_k)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"LLM call failed: {e}")


@app.get("/documents")
def documents():
    col = get_collection()
    data = col.get()
    seen: dict[str, str] = {}
    for m in data.get("metadatas", []) or []:
        if m and m.get("doc_id"):
            seen[m["doc_id"]] = m.get("filename", "?")
    return [{"doc_id": k, "filename": v} for k, v in seen.items()]


@app.delete("/documents/{doc_id}")
def delete_doc(doc_id: str):
    col = get_collection()
    data = col.get(where={"doc_id": doc_id})
    ids = data.get("ids", [])
    if not ids:
        raise HTTPException(404, "doc not found")
    col.delete(ids=ids)
    return {"deleted": doc_id, "chunks": len(ids)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
