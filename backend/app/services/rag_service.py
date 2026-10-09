import logging
import time
from typing import Any

import numpy as np
from fastembed import TextEmbedding
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.telemetry import RETRIEVAL_LATENCY_SECONDS, trace_span
from backend.app.models.entities import (
    AuditEvent,
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
    Project,
)

logger = logging.getLogger(__name__)

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
        Output vector is unit-normalized (L2 norm = 1.0) so dot product equals cosine similarity.
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
        """Generate embeddings in batch for high ingestion throughput with unit normalization."""
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
        user_id: str | None = None,
        org_id: str | None = None,
    ) -> KnowledgeDocument:
        if not org_id:
            raise ValueError(
                "Mandatory tenant context missing: org_id is required for document ingestion."
            )
        if not user_id:
            raise ValueError(
                "Mandatory user context missing: user_id is required for document ingestion."
            )

        # 1. Verify knowledge base exists and belongs to the caller's organization
        query = (
            select(KnowledgeBase)
            .join(Project, KnowledgeBase.project_id == Project.id)
            .where(KnowledgeBase.id == knowledge_base_id, Project.organization_id == org_id)
        )
        res_kb = await db.execute(query)
        kb = res_kb.scalar_one_or_none()
        if not kb:
            raise ValueError(
                f"Knowledge base with id '{knowledge_base_id}' not found or unauthorized for organization '{org_id}'."
            )

        res_p = await db.execute(select(Project).where(Project.id == kb.project_id))
        proj = res_p.scalar_one_or_none()
        audit_org = proj.organization_id if proj else org_id

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
            organization_id=audit_org,
            user_id=user_id,
            action="knowledge:ingest",
            resource_type="document",
            resource_id=doc.id,
            metadata_json={
                "title": title,
                "chunks": len(chunk_entities),
                "embedding_model": cls.EMBEDDING_MODEL_NAME,
            },
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
        org_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute semantic retrieval with consistent score semantics across backends:
        - Embeddings are L2 unit-normalized.
        - similarity = dot(query_vec, chunk_vec) in range [0.0, 1.0].
        - distance = 1.0 - similarity.
        - Filters by min_score and respects tenant boundaries.
        """
        # Tenant ownership validation
        if not org_id:
            raise ValueError(
                "Mandatory tenant context missing: org_id is required for knowledge queries."
            )

        res_kb = await db.execute(
            select(KnowledgeBase)
            .join(Project, KnowledgeBase.project_id == Project.id)
            .where(KnowledgeBase.id == knowledge_base_id, Project.organization_id == org_id)
        )
        if not res_kb.scalar_one_or_none():
            raise ValueError(
                f"Knowledge base '{knowledge_base_id}' not found or unauthorized for organization '{org_id}'."
            )

        with trace_span(
            "rag.vector_retrieval",
            {
                "knowledge_base_id": knowledge_base_id,
                "query_terms": len(query.split()),
                "top_k": top_k,
            },
        ):
            start_time = time.time()

            # 1. Generate real query embedding (unit-normalized)
            query_vec = np.array(cls.generate_embedding(query), dtype=float)

            # 2. Check if database supports native pgvector cosine distance query
            bind = db.get_bind()
            if bind and bind.dialect.name == "postgresql":
                try:
                    stmt = (
                        select(
                            KnowledgeChunk,
                            KnowledgeChunk.embedding.cosine_distance(query_vec.tolist()).label(
                                "distance"
                            ),
                        )
                        .where(KnowledgeChunk.knowledge_base_id == knowledge_base_id)
                        .order_by("distance")
                        .limit(top_k)
                    )
                    res = await db.execute(stmt)
                    rows = res.all()

                    formatted: list[dict[str, Any]] = []
                    for ch, dist in rows:
                        dist_val = float(dist)
                        # Cosine similarity for normalized vectors is (1.0 - distance)
                        sim = max(0.0, min(1.0, 1.0 - dist_val))
                        if sim >= min_score:
                            formatted.append(
                                {
                                    "chunk_id": ch.id,
                                    "document_id": ch.document_id,
                                    "score": round(sim, 4),
                                    "distance": round(dist_val, 4),
                                    "source": ch.metadata_json.get("source", "unknown"),
                                    "title": ch.metadata_json.get("title", "Untitled"),
                                    "text": ch.content,
                                }
                            )
                    duration = time.time() - start_time
                    RETRIEVAL_LATENCY_SECONDS.labels(knowledge_base_id=knowledge_base_id).observe(
                        duration
                    )
                    return formatted
                except Exception as ex:
                    logger.debug("pgvector native operator query fell back: %s", ex)

            # 3. Universal vector similarity retrieval (SQLite / fallback)
            res = await db.execute(
                select(KnowledgeChunk).where(KnowledgeChunk.knowledge_base_id == knowledge_base_id)
            )
            chunks = res.scalars().all()

            scored_results: list[tuple[float, float, KnowledgeChunk]] = []
            for ch in chunks:
                vec_data = ch.embedding if ch.embedding is not None else ch.embedding_json
                if not vec_data:
                    continue
                chunk_vec = np.array(vec_data, dtype=float)
                # Dot product of normalized vectors equals cosine similarity
                dot_sim = float(np.dot(query_vec, chunk_vec))
                sim = max(0.0, min(1.0, dot_sim))
                dist = max(0.0, min(1.0, 1.0 - sim))

                if sim >= min_score:
                    scored_results.append((sim, dist, ch))

            # Sort by semantic similarity descending
            scored_results.sort(key=lambda x: x[0], reverse=True)
            top_results = scored_results[:top_k]

            formatted_fallback: list[dict[str, Any]] = []
            for sim, dist, ch in top_results:
                formatted_fallback.append(
                    {
                        "chunk_id": ch.id,
                        "document_id": ch.document_id,
                        "score": round(sim, 4),
                        "distance": round(dist, 4),
                        "source": ch.metadata_json.get("source", "unknown"),
                        "title": ch.metadata_json.get("title", "Untitled"),
                        "text": ch.content,
                    }
                )

            duration = time.time() - start_time
            RETRIEVAL_LATENCY_SECONDS.labels(knowledge_base_id=knowledge_base_id).observe(duration)
            return formatted_fallback
