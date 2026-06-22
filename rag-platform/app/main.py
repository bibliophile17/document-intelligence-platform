"""
main.py
FastAPI backend for the Enterprise Document Intelligence Platform.

Endpoints:
  POST /api/upload      - upload and index a document (PDF/DOCX/TXT)
  POST /api/query        - ask a natural-language question
  GET  /api/documents     - list indexed documents
  DELETE /api/documents/{doc_id} - remove a document from the index
  GET  /api/status        - health check + Ollama availability
  GET  /                  - serves the chat UI
"""

import os
import shutil
import uuid
import time
import logging
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.document_parser import parse_document
from app.chunker import chunk_text
from app.vector_store import get_vector_store
from app.llm import generate_answer, is_ollama_available

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag-platform")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE_MB = 25

app = FastAPI(title="Enterprise Document Intelligence Platform")

# Audit log (simple in-memory + file log, simulating enterprise audit logging)
AUDIT_LOG_PATH = os.path.join(BASE_DIR, "storage", "audit_log.txt")


def audit_log(action: str, detail: str):
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {action}: {detail}\n")


class QueryRequest(BaseModel):
    question: str
    top_k: int = 4


class QueryResponse(BaseModel):
    answer: str
    mode: str
    sources: List[dict]


@app.on_event("startup")
def startup_event():
    logger.info("Starting up — loading embedding model (this may take a moment on first run)...")
    get_vector_store()
    logger.info(f"Ollama LLM available: {is_ollama_available()}")


@app.get("/api/status")
def status():
    store = get_vector_store()
    return {
        "status": "ok",
        "indexed_chunks": store.count(),
        "ollama_available": is_ollama_available(),
        "ollama_note": "Install Ollama (https://ollama.com) and run 'ollama pull llama3.2' for generated answers. Without it, the app returns the most relevant passages directly.",
    }


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    doc_id = uuid.uuid4().hex[:12]
    safe_filename = f"{doc_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"File exceeds {MAX_FILE_SIZE_MB}MB limit.")

    try:
        text = parse_document(file_path)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Failed to parse document: {e}")

    if not text.strip():
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="No extractable text found in document.")

    chunks = chunk_text(text)
    store = get_vector_store()
    num_added = store.add_chunks(chunks, source_filename=file.filename, doc_id=doc_id)

    audit_log("UPLOAD", f"doc_id={doc_id} filename={file.filename} chunks={num_added}")

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "chunks_indexed": num_added,
        "message": f"Successfully indexed '{file.filename}' into {num_added} chunks.",
    }


@app.post("/api/query", response_model=QueryResponse)
def query_documents(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    store = get_vector_store()
    if store.count() == 0:
        return QueryResponse(
            answer="No documents have been uploaded yet. Upload a PDF, DOCX, or TXT file first.",
            mode="none",
            sources=[],
        )

    hits = store.query(req.question, top_k=req.top_k)
    result = generate_answer(req.question, hits)

    audit_log("QUERY", f"question='{req.question}' mode={result['mode']} hits={len(hits)}")

    return QueryResponse(
        answer=result["answer"],
        mode=result["mode"],
        sources=[
            {"source": h["source"], "relevance_score": h["relevance_score"], "preview": h["text"][:200]}
            for h in hits
        ],
    )


@app.get("/api/documents")
def list_documents():
    store = get_vector_store()
    return {"documents": store.list_documents()}


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str):
    store = get_vector_store()
    deleted = store.delete_document(doc_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Document not found.")
    audit_log("DELETE", f"doc_id={doc_id} chunks_removed={deleted}")
    return {"message": f"Deleted {deleted} chunks for document {doc_id}."}


# Serve frontend
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
