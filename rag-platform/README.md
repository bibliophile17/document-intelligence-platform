# Enterprise Document Intelligence Platform (RAG-Based AI Assistant)

A fully local, **100% free** Retrieval-Augmented Generation (RAG) system.
Upload PDF/DOCX/TXT documents, then ask natural-language questions about
their contents. No API keys, no paid services, no internet required after
initial setup.

## How it works (architecture)

```
Upload → Parse (pypdf/docx) → Chunk (overlapping) → Embed (sentence-transformers)
       → Store (ChromaDB, local) → Query → Retrieve top-k chunks
       → Generate answer (Ollama, local LLM) → Return with source citations
```

- **Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`) — runs on your
  CPU, downloads once (~80MB), no API key.
- **Vector database**: ChromaDB — stores everything in `./storage/`, persists
  across restarts, supports incremental indexing (add new docs without
  re-indexing existing ones).
- **LLM**: [Ollama](https://ollama.com) — free, runs locally. If it's not
  installed/running, the app **still works**: it falls back to returning the
  most relevant passages directly ("extractive mode") instead of failing.
- **Backend**: FastAPI
- **Frontend**: single static HTML/JS file, no build step, no Node required.

---

## Setup (VS Code)

### 1. Open the project folder
Open the `rag-platform` folder in VS Code (`File > Open Folder...`).

### 2. Create a virtual environment
Open a terminal in VS Code (`` Ctrl+` ``) and run:

```bash
python -m venv venv
```

Activate it:
- **Windows**: `venv\Scripts\activate`
- **Mac/Linux**: `source venv/bin/activate`

VS Code may also prompt you in the bottom-right to select this venv as your
Python interpreter — click "Yes".

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, ChromaDB, sentence-transformers, pypdf, python-docx,
etc. — all free/open-source, no API keys needed.

### 4. (Optional but recommended) Install Ollama for generated answers

Without this step, the app still runs and answers questions by returning the
most relevant document passages directly. With Ollama, you get natural
synthesized answers instead.

1. Download Ollama: https://ollama.com/download (free, Windows/Mac/Linux)
2. Install it, then in a terminal run:
   ```bash
   ollama pull llama3.2
   ```
   (This downloads a free ~2GB local model. You can substitute any model you
   prefer, e.g. `phi3`, `mistral` — just update `OLLAMA_MODEL` in
   `app/llm.py` to match.)
3. Ollama runs automatically in the background after install. Verify with:
   ```bash
   ollama list
   ```

### 5. Run the app

```bash
uvicorn app.main:app --reload --port 8000
```

The first run will download the embedding model (~80MB) — this is a one-time
download. You'll see `Embedding model ready.` in the terminal when it's done.

### 6. Open the app

Go to **http://localhost:8000** in your browser.

---

## Using the app

1. **Upload**: drag a PDF, DOCX, or TXT file onto the upload zone (left
   panel), or click it to browse. The file is parsed, split into overlapping
   chunks, embedded, and indexed — you'll see it appear in the document list.
2. **Ask**: type a question in the chat box on the right. The system:
   - Embeds your question
   - Retrieves the most relevant chunks from ChromaDB (cosine similarity)
   - If Ollama is running, sends those chunks + your question to the LLM to
     generate a synthesized answer
   - If not, returns the top relevant passages directly, clearly labeled
     "extractive mode"
3. **Manage documents**: each indexed document can be removed individually
   (×  button) — this deletes only that document's chunks, leaving the rest
   of the index untouched (incremental indexing, not full rebuild).

## Project structure

```
rag-platform/
├── app/
│   ├── main.py              # FastAPI app, REST endpoints
│   ├── document_parser.py   # PDF/DOCX/TXT text extraction
│   ├── chunker.py           # Overlapping text chunking
│   ├── vector_store.py      # ChromaDB + sentence-transformers wrapper
│   └── llm.py                # Ollama integration + extractive fallback
├── static/
│   └── index.html            # Frontend (no build step needed)
├── uploads/                  # Uploaded files land here
├── storage/                  # ChromaDB persistent storage + audit log
├── requirements.txt
└── README.md
```

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `GET`  | `/api/status` | Health check, chunk count, Ollama availability |
| `POST` | `/api/upload` | Upload + index a document (multipart form, field `file`) |
| `POST` | `/api/query` | `{"question": "...", "top_k": 4}` → answer + sources |
| `GET`  | `/api/documents` | List indexed documents |
| `DELETE` | `/api/documents/{doc_id}` | Remove a document from the index |

## Notes on the resume claims this project supports

- **"Reduced manual document search time"** — demonstrated via the
  retrieval step: semantic search returns relevant passages instantly vs.
  manually reading documents.
- **"Incremental updates without full re-indexing"** — `add_chunks()` only
  embeds and inserts new content; existing vectors are untouched.
  `delete_document()` removes only that document's vectors.
- **"Role-based access control / audit logging"** — the current build
  includes audit logging (`storage/audit_log.txt` records every upload,
  query, and delete with timestamps). Access control is intentionally not
  included since it requires an auth/session layer — see "Extending this
  project" below if you want to add it honestly before claiming it on a
  resume.
- **"Setup runbooks / architecture documentation"** — this README.

## Extending this project (optional, if you want to deepen it further)

- **Auth**: add `fastapi-users` or a simple API-key middleware to gate
  upload/query endpoints — this is what would let you honestly claim
  "role-based access control."
- **Docker**: add a `Dockerfile` + `docker-compose.yml` to containerize this
  (FastAPI + persistent volume for `storage/`) — directly supports a
  "one-command deployment" resume claim.
- **Streaming answers**: Ollama supports streaming responses; swap
  `stream: False` to `True` in `app/llm.py` and use FastAPI's
  `StreamingResponse` for a token-by-token typing effect.

## Troubleshooting

- **"Embedding model ready" takes a long time on first run**: this is
  normal — it's downloading `all-MiniLM-L6-v2` (~80MB) once. Subsequent
  runs are fast.
- **Ollama shows as unavailable**: make sure `ollama serve` is running (it
  usually auto-starts after install) and that you've run
  `ollama pull llama3.2`.
- **PDF text extraction returns nothing**: scanned/image-only PDFs have no
  embedded text layer. This project does not include OCR — you'd need to
  add `pytesseract` for that.
- **Port 8000 already in use**: run with a different port, e.g.
  `uvicorn app.main:app --reload --port 8001`.
