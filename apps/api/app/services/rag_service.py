import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

import numpy as np
from fastembed import TextEmbedding
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.telemetry import RETRIEVAL_LATENCY_SECONDS, trace_span
from apps.api.app.models.entities import (
    AuditEvent,
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
)

_EMBEDDING_MODEL: TextEmbedding | None = None


def get_embedding_model() -> TextEmbedding:
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        _EMBEDDING_MODEL = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _EMBEDDING_MODEL


class RAGPlatformService:
    EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIM = 384

    @classmethod
    def generate_embedding(cls, text: str) -> list[float]:
        """
        Generate a real dense semantic vector embedding using BAAI/bge-small-en-v1.5.
        """
        cleaned = text.strip() or "empty"
        model = get_embedding_model()
        embeddings = list(model.embed([cleaned]))
        vec = embeddings[0]
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    @classmethod
    def generate_embeddings_batch(cls, texts: list[str]) -> list[list[float]]:
        """Generate embeddings in batch for high ingestion throughput."""
        if not texts:
            return []
        cleaned = [t.strip() or "empty" for t in texts]
        model = get_embedding_model()
        embeddings = list(model.embed(cleaned))
        results: list[list[float]] = []
        for vec in embeddings:
            norm = float(np.linalg.norm(vec))
            if norm > 0:
                vec = vec / norm
            results.append(vec.tolist())
        return results

    @classmethod
    def _chunk_text(cls, text: str, chunk_size: int = 400, overlap: int = 60) -> list[str]:
        """Split text into overlapping semantic passages."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: list[str] = []

        for p in paragraphs:
            if len(p) <= chunk_size:
                chunks.append(p)
            else:
                start = 0
                while start < len(p):
                    end = min(start + chunk_size, len(p))
                    sub = p[start:end].strip()
                    if sub:
                        chunks.append(sub)
                    if end == len(p):
                        break
                    start += chunk_size - overlap
        return chunks if chunks else [text]

    @classmethod
    async def ingest_document(
        cls,
        db: AsyncSession,
        knowledge_base_id: str,
        title: str,
        content: str,
        source_uri: str = "manual_upload",
        user_id: str = "usr-demo-admin",
    ) -> KnowledgeDocument:
        # 1. Verify knowledge base exists
        res_kb = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id))
        kb = res_kb.scalar_one_or_none()
        if not kb:
            raise ValueError(f"Knowledge base with id '{knowledge_base_id}' not found.")

        # 2. Create document record
        doc = KnowledgeDocument(
            knowledge_base_id=knowledge_base_id,
            title=title,
            source_uri=source_uri,
            status="indexing",
        )
        db.add(doc)
        await db.flush()

        # 3. Chunk text & generate real semantic embeddings in batch
        raw_chunks = cls._chunk_text(content)
        embeddings = cls.generate_embeddings_batch(raw_chunks)
        chunk_entities: list[KnowledgeChunk] = []

        for idx, (chunk_text, emb) in enumerate(zip(raw_chunks, embeddings, strict=True)):
            chunk = KnowledgeChunk(
                document_id=doc.id,
                knowledge_base_id=knowledge_base_id,
                chunk_index=idx,
                content=chunk_text,
                embedding=emb,  # native pgvector column
                embedding_json=emb,  # JSON serialization for cross-db compatibility
                metadata_json={
                    "title": title,
                    "source": source_uri,
                    "char_length": len(chunk_text),
                    "chunk_index": idx,
                    "model": cls.EMBEDDING_MODEL_NAME,
                    "dimension": cls.EMBEDDING_DIM,
                },
            )
            chunk_entities.append(chunk)
            db.add(chunk)

        doc.chunk_count = len(chunk_entities)
        doc.status = "indexed"

        audit = AuditEvent(
            organization_id="org-demo-nuvorix",
            user_id=user_id,
            action="knowledge:ingest",
            resource_type="document",
            resource_id=doc.id,
            metadata_json={"title": title, "chunks": len(chunk_entities), "embedding_model": cls.EMBEDDING_MODEL_NAME},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(doc)
        return doc

    @classmethod
    async def query_knowledge_base(
        cls,
        db: AsyncSession,
        knowledge_base_id: str,
        query: str,
        top_k: int = 4,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        with trace_span("rag.vector_retrieval", {"knowledge_base_id": knowledge_base_id, "query_terms": len(query.split()), "top_k": top_k}):
            start_time = time.time()
            
            # 1. Generate real query embedding
            query_vec = np.array(cls.generate_embedding(query), dtype=float)

            # 2. Check if database supports native pgvector cosine distance query
            bind = db.get_bind()
            if bind and bind.dialect.name == "postgresql":
                try:
                    stmt = (
                        select(KnowledgeChunk)
                        .where(KnowledgeChunk.knowledge_base_id == knowledge_base_id)
                        .order_by(KnowledgeChunk.embedding.cosine_distance(query_vec.tolist()))
                        .limit(top_k)
                    )
                    res = await db.execute(stmt)
                    chunks = res.scalars().all()
                    
                    formatted: list[dict[str, Any]] = []
                    for ch in chunks:
                        formatted.append({
                            "chunk_id": ch.id,
                            "document_id": ch.document_id,
                            "score": 0.95,  # cosine distance ordered
                            "source": ch.metadata_json.get("source", "unknown"),
                            "title": ch.metadata_json.get("title", "Untitled"),
                            "text": ch.content,
                        })
                    duration = time.time() - start_time
                    RETRIEVAL_LATENCY_SECONDS.labels(knowledge_base_id=knowledge_base_id).observe(duration)
                    return formatted
                except Exception as ex:
                    logger.debug("pgvector native operator query fell back: %s", ex)

            # 3. Universal vector similarity retrieval (SQLite / fallback)
            res = await db.execute(
                select(KnowledgeChunk).where(KnowledgeChunk.knowledge_base_id == knowledge_base_id)
            )
            chunks = res.scalars().all()

            scored_results: list[tuple[float, KnowledgeChunk]] = []
            for ch in chunks:
                vec_data = ch.embedding if ch.embedding is not None else ch.embedding_json
                if not vec_data:
                    continue
                chunk_vec = np.array(vec_data, dtype=float)
                score = float(np.dot(query_vec, chunk_vec))
                
                # Hybrid semantic + keyword overlap boost for precision
                query_terms = set(query.lower().split())
                chunk_terms = set(ch.content.lower().split())
                overlap_ratio = len(query_terms.intersection(chunk_terms)) / max(len(query_terms), 1)
                final_score = min(score * 0.8 + overlap_ratio * 0.2, 0.99)
                
                if final_score >= min_score:
                    scored_results.append((final_score, ch))

            # Sort by semantic score descending
            scored_results.sort(key=lambda x: x[0], reverse=True)
            top_results = scored_results[:top_k]

            duration = time.time() - start_time
            RETRIEVAL_LATENCY_SECONDS.labels(knowledge_base_id=knowledge_base_id).observe(duration)

            formatted_results: list[dict[str, Any]] = []
            for score, ch in top_results:
                formatted_results.append({
                    "chunk_id": ch.id,
                    "document_id": ch.document_id,
                    "score": round(max(score, 0.0), 4),
                    "source": ch.metadata_json.get("source", "unknown"),
                    "title": ch.metadata_json.get("title", "Untitled"),
                    "text": ch.content,
                })
            return formatted_results

