# 📄 Document Intelligence Platform

> Ask natural-language questions about your documents — fully local, 100% free, no API key required.

A production-inspired **Retrieval-Augmented Generation (RAG)** system built with FastAPI, ChromaDB, and sentence-transformers. Upload PDF, DOCX, or TXT files and instantly query them using natural language. The system finds the most semantically relevant passages and generates a synthesized answer using a fully local LLM — nothing leaves your machine.

## How It Works

```
Upload → Parse (PDF/DOCX/TXT) → Chunk (overlapping) → Embed (sentence-transformers)
                                                              ↓
                                                       ChromaDB (local)
                                                              ↓
Question → Embed → Retrieve top-k chunks (cosine similarity) → Ollama LLM → Answer + Sources
```

- **No API key needed** — embeddings run locally via `sentence-transformers`
- **No cloud dependency** — vector store is ChromaDB, persisted on disk
- **Graceful fallback** — if Ollama isn't installed, the app returns the most relevant passages directly ("extractive mode") instead of failing
- **Incremental indexing** — add new documents without rebuilding the entire vector store

---

## Tech Stack

| Layer            | Technology                                 |
| ---------------- | ------------------------------------------ |
| Backend          | FastAPI, Python 3.10+                      |
| Embeddings       | sentence-transformers (`all-MiniLM-L6-v2`) |
| Vector Database  | ChromaDB (persistent, local)               |
| LLM              | Ollama — llama3.2 (optional, local)        |
| Document Parsing | pypdf, python-docx                         |
| Frontend         | Vanilla HTML / CSS / JS (no build step)    |

---

## Features

- 🔍 **Semantic search** across multiple documents simultaneously (not keyword matching)
- 🤖 **Local LLM answer generation** via Ollama — fully offline after setup
- 📎 **Source citations** — every answer shows which document it came from and a relevance score
- ➕ **Incremental indexing** — upload new docs without re-indexing existing ones
- 🗑️ **Per-document deletion** — remove one document's vectors without affecting the rest
- 📋 **Audit logging** — every upload, query, and delete is timestamped and logged to disk
- 🌐 **REST API** — all functionality exposed via clean documented endpoints
- 💻 **No build step** — frontend is a single HTML file, works out of the box

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/bibliophile17/document-intelligence-platform.git
cd document-intelligence-platform
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
python -m uvicorn app.main:app --reload --port 8000
```

> First run downloads the embedding model (~80MB, one time only). You'll see `Embedding model ready.` when it's done.

### 5. Open in browser

```
http://localhost:8000
```

---

## Optional — Enable Local LLM (Ollama)

Without Ollama the app works in **extractive mode** — it returns the most relevant passages directly.
With Ollama you get proper **synthesized, natural-language answers**.

1. Download and install Ollama from https://ollama.com (free, Windows/Mac/Linux)
2. Pull a model:

```bash
ollama pull llama3.2
```

3. Restart the app — the status bar will show **"LLM engine connected"**

You can swap to any model you prefer (`phi3`, `mistral`, etc.) by changing `OLLAMA_MODEL` in `app/llm.py`.

---

## Project Structure

```
document-intelligence-platform/
├── app/
│   ├── main.py              # FastAPI app and all REST endpoints
│   ├── document_parser.py   # PDF, DOCX, TXT text extraction
│   ├── chunker.py           # Overlapping text chunking logic
│   ├── vector_store.py      # ChromaDB + sentence-transformers wrapper
│   └── llm.py               # Ollama integration + extractive fallback
├── static/
│   └── index.html           # Frontend UI (no build step needed)
├── uploads/                 # Uploaded files stored here
├── storage/                 # ChromaDB vectors + audit log (auto-created)
├── requirements.txt
└── README.md
```

---

## API Reference

| Method   | Endpoint                  | Description                                          |
| -------- | ------------------------- | ---------------------------------------------------- |
| `GET`    | `/api/status`             | Health check, chunk count, Ollama availability       |
| `POST`   | `/api/upload`             | Upload and index a document (PDF/DOCX/TXT)           |
| `POST`   | `/api/query`              | `{"question": "...", "top_k": 4}` → answer + sources |
| `GET`    | `/api/documents`          | List all indexed documents                           |
| `DELETE` | `/api/documents/{doc_id}` | Remove a document from the index                     |

Interactive API docs available at `http://localhost:8000/docs` (Swagger UI, auto-generated by FastAPI).

---

## Troubleshooting

| Problem                    | Fix                                                                                    |
| -------------------------- | -------------------------------------------------------------------------------------- |
| Slow first startup         | Normal — downloading embedding model once (~80MB)                                      |
| Ollama shows unavailable   | Run `ollama serve` or reinstall from https://ollama.com                                |
| PDF returns no text        | Scanned/image PDFs have no text layer — OCR not included                               |
| Port 8000 in use           | Use `--port 8001` and open `http://localhost:8001`                                     |
| `ModuleNotFoundError: app` | Make sure your terminal is inside the project folder, then use `python -m uvicorn ...` |

---

## Roadmap / Possible Extensions

- [ ] Docker + docker-compose for one-command deployment
- [ ] JWT authentication and role-based access control
- [ ] Streaming LLM responses (token-by-token)
- [ ] OCR support for scanned PDFs via pytesseract
- [ ] Multi-user support with per-user document isolation

---
