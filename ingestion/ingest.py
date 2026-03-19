#!/usr/bin/env python3
"""
NURA Handbook Ingestion Script
Reads PDF/DOCX/TXT files from handbook/, embeds with Ollama nomic-embed-text,
stores in ChromaDB collection 'nura_handbook'.
"""
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

HANDBOOK_DIR = os.environ.get("HANDBOOK_DIR", "/app/handbook")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
CHROMA_HOST = os.environ.get("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8001"))
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")
CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "64"))


def main():
    try:
        import chromadb
        from llama_index.core import (
            Settings,
            SimpleDirectoryReader,
            StorageContext,
            VectorStoreIndex,
        )
        from llama_index.embeddings.ollama import OllamaEmbedding
        from llama_index.vector_stores.chroma import ChromaVectorStore
    except ImportError as e:
        logger.error(f"Missing dependency: {e}. Run: pip install -r requirements.txt")
        sys.exit(1)

    handbook_path = Path(HANDBOOK_DIR)
    if not handbook_path.exists():
        logger.error(f"Handbook directory not found: {HANDBOOK_DIR}")
        sys.exit(1)

    files = [
        f for f in handbook_path.rglob("*")
        if f.suffix.lower() in {".pdf", ".docx", ".txt", ".md"}
        and f.name != ".gitkeep"
    ]

    if not files:
        logger.warning(f"No handbook files found in {HANDBOOK_DIR}")
        logger.info("Place .pdf, .docx, .txt, or .md files there and re-run.")
        return

    logger.info(f"Found {len(files)} file(s): {[f.name for f in files]}")

    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

    try:
        chroma_client.delete_collection("nura_handbook")
        logger.info("Deleted existing nura_handbook collection")
    except Exception:
        pass

    collection = chroma_client.create_collection("nura_handbook")
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    embed_model = OllamaEmbedding(
        model_name=EMBEDDING_MODEL, base_url=OLLAMA_HOST
    )
    Settings.embed_model = embed_model
    Settings.chunk_size = CHUNK_SIZE
    Settings.chunk_overlap = CHUNK_OVERLAP

    logger.info("Loading documents...")
    documents = SimpleDirectoryReader(
        str(handbook_path), recursive=True
    ).load_data()

    logger.info(f"Indexing {len(documents)} document(s)...")
    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True,
    )

    count = collection.count()
    logger.info(f"Done! {count} chunks stored in ChromaDB.")
    print(f"\n✅ SUCCESS: {count} chunks ingested from {len(files)} file(s)")


if __name__ == "__main__":
    main()
