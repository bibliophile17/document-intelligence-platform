"""
llm.py
Generates natural-language answers from retrieved chunks.

Primary mode: Ollama (https://ollama.com) — 100% free, runs locally,
no API key, no internet required after model download.

Fallback mode: if Ollama isn't running, the app still works — it returns
the most relevant retrieved passages directly ("extractive" answer) so the
RAG pipeline is never blocked on having an LLM installed.
"""

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"  # free local model, swap for any model you've pulled

SYSTEM_PROMPT = """You are an enterprise document assistant. Answer the user's question
using ONLY the provided context excerpts from internal documents. If the answer isn't
contained in the context, say so clearly instead of guessing. Always be concise and
reference which source document(s) you used."""


def is_ollama_available() -> bool:
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False


def build_prompt(question: str, context_chunks: list) -> str:
    context_block = "\n\n".join(
        f"[Source: {c['source']}, chunk {c['chunk_index']}]\n{c['text']}"
        for c in context_chunks
    )
    return f"""{SYSTEM_PROMPT}

CONTEXT:
{context_block}

QUESTION: {question}

ANSWER:"""


def generate_answer_ollama(question: str, context_chunks: list) -> str:
    prompt = build_prompt(question, context_chunks)
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.RequestException as e:
        return f"[Ollama error: {e}] Falling back to extractive answer below."


def generate_answer_extractive(question: str, context_chunks: list) -> str:
    """
    No-LLM fallback: stitches together the most relevant retrieved
    passages directly. Ensures the app is fully functional even
    without any LLM installed.
    """
    if not context_chunks:
        return "No relevant information was found in the indexed documents."

    lines = ["No local LLM detected (Ollama not running) — showing the most relevant passages found instead:\n"]
    for c in context_chunks:
        lines.append(f"From **{c['source']}** (relevance: {c['relevance_score']}):\n{c['text']}\n")
    return "\n".join(lines)


def generate_answer(question: str, context_chunks: list) -> dict:
    """
    Main entry point. Tries Ollama first, falls back to extractive mode.
    Returns dict with 'answer' and 'mode' ("llm" or "extractive").
    """
    if not context_chunks:
        return {
            "answer": "No relevant information was found in the indexed documents for this question.",
            "mode": "none",
        }

    if is_ollama_available():
        answer = generate_answer_ollama(question, context_chunks)
        return {"answer": answer, "mode": "llm"}
    else:
        answer = generate_answer_extractive(question, context_chunks)
        return {"answer": answer, "mode": "extractive"}
