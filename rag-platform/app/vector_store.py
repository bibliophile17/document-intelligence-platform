"""
vector_store.py
Wraps ChromaDB (local, free, persistent vector database) and
sentence-transformers (local, free embedding model — no API key needed).

This mirrors the "ingestion pipeline" pattern: chunk -> embed -> index,
with support for incremental updates (adding new docs without re-indexing
everything).
"""

import os
import uuid
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
COLLECTION_NAME = "documents"

# Small, fast, fully local embedding model (~80MB download, runs on CPU)
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


class VectorStore:
    def __init__(self):
        os.makedirs(STORAGE_DIR, exist_ok=True)

        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        self.client = chromadb.PersistentClient(
            path=STORAGE_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        print(f"Loading embedding model '{EMBEDDING_MODEL_NAME}' (first run downloads it)...")
        self.embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print("Embedding model ready.")

    def embed(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.embedder.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return embeddings.tolist()

    def add_chunks(
        self,
        chunks: List[str],
        source_filename: str,
        doc_id: str,
    ) -> int:
        """
        Embed and store chunks for a document. Incremental — only
        embeds and inserts the new chunks passed in, doesn't touch
        existing documents in the collection.
        """
        if not chunks:
            return 0

        embeddings = self.embed(chunks)
        ids = [f"{doc_id}_chunk_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]
        metadatas = [
            {"source": source_filename, "doc_id": doc_id, "chunk_index": i}
            for i in range(len(chunks))
        ]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )
        return len(chunks)

    def query(self, question: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Return the top_k most relevant chunks for a question."""
        query_embedding = self.embed([question])[0]

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        hits = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                hits.append({
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    "chunk_index": meta.get("chunk_index", -1),
                    "relevance_score": round(1 - distance, 4),  # cosine distance -> similarity
                })
        return hits

    def list_documents(self) -> List[Dict[str, Any]]:
        """Return distinct source documents currently indexed."""
        all_items = self.collection.get(include=["metadatas"])
        seen = {}
        for meta in all_items["metadatas"]:
            doc_id = meta.get("doc_id")
            if doc_id not in seen:
                seen[doc_id] = {"doc_id": doc_id, "source": meta.get("source"), "chunks": 0}
            seen[doc_id]["chunks"] += 1
        return list(seen.values())

    def delete_document(self, doc_id: str) -> int:
        """Remove all chunks belonging to a document (by doc_id)."""
        existing = self.collection.get(where={"doc_id": doc_id})
        ids_to_delete = existing["ids"]
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
        return len(ids_to_delete)

    def count(self) -> int:
        return self.collection.count()


# Singleton instance shared across the app
_store_instance = None


def get_vector_store() -> VectorStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = VectorStore()
    return _store_instance
