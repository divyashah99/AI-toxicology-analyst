"""ChromaDB persistent client. Single collection per workspace (MVP)."""
from __future__ import annotations

from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings

_COLLECTION = "papers"
_client: chromadb.api.ClientAPI | None = None


def _get_client() -> chromadb.api.ClientAPI:
    global _client
    if _client is None:
        s = get_settings()
        _client = chromadb.PersistentClient(
            path=s.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def collection() -> chromadb.api.models.Collection.Collection:
    return _get_client().get_or_create_collection(
        name=_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(
    ids: list[str],
    documents: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict[str, Any]],
) -> None:
    collection().add(
        ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
    )


def query(
    embedding: list[float],
    k: int = 6,
    paper_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    where = {"paper_id": {"$in": paper_ids}} if paper_ids else None
    res = collection().query(
        query_embeddings=[embedding], n_results=k, where=where
    )
    out: list[dict[str, Any]] = []
    if not res.get("ids") or not res["ids"][0]:
        return out
    for i, doc_id in enumerate(res["ids"][0]):
        out.append(
            {
                "id": doc_id,
                "text": res["documents"][0][i],
                "metadata": res["metadatas"][0][i],
                "distance": res["distances"][0][i],
                "score": 1.0 - res["distances"][0][i],
            }
        )
    return out


def delete_paper(paper_id: str) -> None:
    collection().delete(where={"paper_id": paper_id})


def count() -> int:
    return collection().count()
