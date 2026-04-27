import asyncio
import logging
from typing import Optional, Tuple

import chromadb
from llama_index.core import Settings as LISettings, StorageContext, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from config import settings

logger = logging.getLogger(__name__)

_index: Optional[VectorStoreIndex] = None
_chroma_client: Optional[chromadb.HttpClient] = None


def get_chroma_client() -> chromadb.HttpClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
    return _chroma_client


def get_index() -> VectorStoreIndex:
    global _index
    if _index is None:
        client = get_chroma_client()
        collection = client.get_or_create_collection("nura_handbook")
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        embed_model = OpenAIEmbedding(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )
        LISettings.embed_model = embed_model
        LISettings.chunk_size = settings.rag_chunk_size
        LISettings.chunk_overlap = settings.rag_chunk_overlap

        _index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
        )
    return _index


async def retrieve_context(query: str) -> Tuple[str, float, Optional[str]]:
    try:
        index = get_index()
        retriever = index.as_retriever(similarity_top_k=settings.rag_top_k)
        nodes = await asyncio.to_thread(retriever.retrieve, query)

        if not nodes:
            return "", 0.0, None

        chunks = [node.get_content() for node in nodes]
        scores = [node.score if node.score else 0.5 for node in nodes]

        context = "\n\n---\n\n".join(chunks)
        avg_score = sum(scores) / len(scores)

        top_meta = nodes[0].node.metadata if nodes else {}
        source_doc = top_meta.get("file_name") or top_meta.get("file_path") or None
        if source_doc:
            source_doc = source_doc.split("/")[-1]  # basename only

        return context, round(avg_score, 3), source_doc
    except Exception as e:
        logger.error(f"RAG retrieval error: {e}")
        return "", 0.0, None


def reset_index() -> None:
    global _index
    _index = None
