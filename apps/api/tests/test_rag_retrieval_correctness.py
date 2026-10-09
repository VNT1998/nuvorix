import uuid

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.app.db.session import AsyncSessionLocal
from apps.api.app.main import app
from apps.api.app.models.entities import KnowledgeBase, KnowledgeChunk, Project
from apps.api.app.services.rag_service import RAGPlatformService


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def test_embedding_generation_properties():
    """Verify generated embeddings are unit-normalized 384-dimensional dense vectors."""
    text1 = "Automated release gates and quality policies in Nuvorix control plane"
    emb1 = RAGPlatformService.generate_embedding(text1)

    assert isinstance(emb1, list)
    assert len(emb1) == 384
    # Unit norm test
    norm = np.linalg.norm(emb1)
    assert pytest.approx(norm, rel=1e-3) == 1.0


@pytest.mark.asyncio
async def test_retrieval_ranking_and_scores():
    """Verify cosine similarity score semantics and ranking correctness."""
    uid = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as session:
        proj = Project(
            id=f"proj-rag-test-{uid}",
            organization_id=f"org-rag-test-{uid}",
            name="RAG Eval Project",
        )
        session.add(proj)
        await session.flush()

        kb = KnowledgeBase(
            id=f"kb-rag-{uid}",
            project_id=proj.id,
            name="RAG Score Verification KB",
            embedding_model="BAAI/bge-small-en-v1.5",
        )
        session.add(kb)
        await session.flush()

        # Ingest Document A (relevant to deployment rollback)
        text_a = "SRE runbook: Automated rollback shifts 100 percent of traffic back to the prior stable deployment."
        emb_a = RAGPlatformService.generate_embedding(text_a)
        chunk_a = KnowledgeChunk(
            id=f"chunk-a-{uid}",
            knowledge_base_id=kb.id,
            document_id=f"doc-a-{uid}",
            chunk_index=0,
            content=text_a,
            embedding=emb_a,
            embedding_json=emb_a,
            metadata_json={"title": "Rollback Runbook"},
        )

        # Ingest Document B (irrelevant topic: dessert recipes)
        text_b = "Chocolate cake recipe: Mix flour, cocoa powder, sugar, and bake at 350 degrees for 30 minutes."
        emb_b = RAGPlatformService.generate_embedding(text_b)
        chunk_b = KnowledgeChunk(
            id=f"chunk-b-{uid}",
            knowledge_base_id=kb.id,
            document_id=f"doc-b-{uid}",
            chunk_index=0,
            content=text_b,
            embedding=emb_b,
            embedding_json=emb_b,
            metadata_json={"title": "Dessert Recipe"},
        )

        session.add(chunk_a)
        session.add(chunk_b)
        await session.commit()

        # Query about deployment rollback
        query = "How do we execute an automated rollback to prior deployment?"
        results = await RAGPlatformService.query_knowledge_base(
            db=session,
            knowledge_base_id=kb.id,
            query=query,
            top_k=2,
            min_score=0.0,
            org_id=f"org-rag-test-{uid}",
        )

        assert len(results) >= 1
        top_result = results[0]

        # Top result must be chunk A
        assert top_result["chunk_id"] == f"chunk-a-{uid}"
        assert "rollback" in top_result["text"].lower()

        # Score semantics: cosine similarity in [0, 1], distance = 1 - similarity
        score = top_result["score"]
        distance = top_result["distance"]
        assert 0.0 <= score <= 1.0
        assert pytest.approx(distance + score, abs=1e-4) == 1.0
        assert score > 0.45  # True semantic relevance threshold


@pytest.mark.asyncio
async def test_min_score_threshold_filtering():
    """Verify that results below min_score are strictly excluded."""
    uid = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as session:
        proj = Project(
            id=f"proj-filter-{uid}", organization_id=f"org-filter-{uid}", name="Filter Project"
        )
        session.add(proj)
        await session.flush()

        kb = KnowledgeBase(id=f"kb-filter-{uid}", project_id=proj.id, name="Filter KB")
        session.add(kb)
        await session.flush()

        text = "Operating system kernel memory scheduling and page table allocation algorithms."
        emb = RAGPlatformService.generate_embedding(text)
        chunk = KnowledgeChunk(
            id=f"chunk-filter-{uid}",
            knowledge_base_id=kb.id,
            document_id=f"doc-filter-{uid}",
            chunk_index=0,
            content=text,
            embedding=emb,
            embedding_json=emb,
        )
        session.add(chunk)
        await session.commit()

        # Query with an unrelated prompt with high min_score threshold
        results = await RAGPlatformService.query_knowledge_base(
            db=session,
            knowledge_base_id=kb.id,
            query="tropical smoothie pineapple banana recipe",
            top_k=5,
            min_score=0.75,
            org_id=f"org-filter-{uid}",
        )

        # Unrelated query with high min_score should return zero results
        assert len(results) == 0


@pytest.mark.asyncio
async def test_multi_tenant_rag_isolation():
    """Verify that querying a knowledge base with wrong org_id returns empty or raises ValueError."""
    uid = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as session:
        proj_owner = Project(
            id=f"proj-owner-{uid}", organization_id=f"org-owner-{uid}", name="Owner Project"
        )
        session.add(proj_owner)
        await session.flush()

        kb = KnowledgeBase(id=f"kb-secure-{uid}", project_id=proj_owner.id, name="Owner Secure KB")
        session.add(kb)
        await session.flush()

        text = "Confidential financial projections and revenue metrics for Q4."
        emb = RAGPlatformService.generate_embedding(text)
        chunk = KnowledgeChunk(
            id=f"chunk-sec-{uid}",
            knowledge_base_id=kb.id,
            document_id=f"doc-sec-{uid}",
            chunk_index=0,
            content=text,
            embedding=emb,
            embedding_json=emb,
        )
        session.add(chunk)
        await session.commit()

        # Rogue tenant attempts to query owner's KB
        with pytest.raises(ValueError, match="not found or unauthorized"):
            await RAGPlatformService.query_knowledge_base(
                db=session,
                knowledge_base_id=kb.id,
                query="financial projections",
                top_k=3,
                org_id=f"org-attacker-{uid}",
            )
