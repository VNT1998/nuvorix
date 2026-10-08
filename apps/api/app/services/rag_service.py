import hashlib
import time
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.telemetry import RETRIEVAL_LATENCY_SECONDS, trace_span
from apps.api.app.models.entities import (
    AuditEvent,
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
)


class RAGPlatformService:
    EMBEDDING_DIM = 64

    @classmethod
    def generate_embedding(cls, text: str) -> list[float]:
        """
        Generate a normalized, dense vector embedding for text.
        Uses multi-hash pseudo-random projection to ensure deterministic,
        semantic-like vector properties with exact cosine similarity behavior.
        """
        tokens = text.lower().replace("\n", " ").split()
        if not tokens:
            vec = np.zeros(cls.EMBEDDING_DIM, dtype=float)
            vec[0] = 1.0
            return vec.tolist()

        vec = np.zeros(cls.EMBEDDING_DIM, dtype=float)
        for token in tokens:
            # Deterministic hash projection
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx = h % cls.EMBEDDING_DIM
            sign = 1.0 if ((h >> 8) % 2 == 0) else -1.0
            weight = 1.0 + (len(token) / 10.0)
            vec[idx] += sign * weight

        # Add 3-gram projection for phrase matching
        for i in range(len(text) - 2):
            gram = text[i : i + 3].lower()
            gh = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
            gidx = gh % cls.EMBEDDING_DIM
            gsign = 1.0 if (gh % 2 == 0) else -1.0
            vec[gidx] += gsign * 0.4

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    @classmethod
    def _chunk_text(cls, text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
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

        # 3. Chunk text & generate embeddings
        raw_chunks = cls._chunk_text(content)
        chunk_entities: list[KnowledgeChunk] = []

        for idx, chunk_text in enumerate(raw_chunks):
            embedding = cls.generate_embedding(chunk_text)
            chunk = KnowledgeChunk(
                document_id=doc.id,
                knowledge_base_id=knowledge_base_id,
                chunk_index=idx,
                content=chunk_text,
                embedding_json=embedding,
                metadata_json={
                    "title": title,
                    "source": source_uri,
                    "char_length": len(chunk_text),
                    "chunk_index": idx,
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
            metadata_json={"title": title, "chunks": len(chunk_entities)},
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
            
            # 1. Generate query embedding
            query_vec = np.array(cls.generate_embedding(query), dtype=float)

            # 2. Fetch all chunks in this knowledge base
            res = await db.execute(
                select(KnowledgeChunk).where(KnowledgeChunk.knowledge_base_id == knowledge_base_id)
            )
            chunks = res.scalars().all()

            scored_results: list[tuple[float, KnowledgeChunk]] = []
            for ch in chunks:
                if not ch.embedding_json:
                    continue
                chunk_vec = np.array(ch.embedding_json, dtype=float)
                score = float(np.dot(query_vec, chunk_vec))
                
                # Additional exact keyword boost for high precision
                query_terms = set(query.lower().split())
                chunk_terms = set(ch.content.lower().split())
                overlap_ratio = len(query_terms.intersection(chunk_terms)) / max(len(query_terms), 1)
                final_score = min(score * 0.7 + overlap_ratio * 0.3, 0.99)
                
                if final_score >= min_score:
                    scored_results.append((final_score, ch))

            # 3. Sort by score descending
            scored_results.sort(key=lambda x: x[0], reverse=True)
            top_results = scored_results[:top_k]

            duration = time.time() - start_time
            RETRIEVAL_LATENCY_SECONDS.labels(knowledge_base_id=knowledge_base_id).observe(duration)

            formatted: list[dict[str, Any]] = []
            for score, ch in top_results:
                formatted.append({
                    "chunk_id": ch.id,
                    "document_id": ch.document_id,
                    "score": round(max(score, 0.0), 4),
                    "source": ch.metadata_json.get("source", "unknown"),
                    "title": ch.metadata_json.get("title", "Untitled"),
                    "text": ch.content,
                })
            return formatted
