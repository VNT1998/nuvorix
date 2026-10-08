
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import UserSession, get_current_user
from apps.api.app.db.session import get_db
from apps.api.app.models.entities import KnowledgeBase, KnowledgeDocument
from apps.api.app.schemas.domain import (
    DocumentIngestRequest,
    DocumentResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    QueryRequest,
    QueryResponse,
    RetrievalChunk,
)
from apps.api.app.services.rag_service import RAGPlatformService

router = APIRouter(tags=["RAG & Knowledge Bases"])


@router.post("/projects/{project_id}/knowledge-bases", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    project_id: str,
    payload: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    kb = KnowledgeBase(
        project_id=project_id,
        name=payload.name,
        description=payload.description or "",
        embedding_model=payload.embedding_model,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return kb


@router.get("/projects/{project_id}/knowledge-bases", response_model=list[KnowledgeBaseResponse])
async def list_project_knowledge_bases(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    res = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.project_id == project_id).order_by(KnowledgeBase.created_at.desc())
    )
    return list(res.scalars().all())


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseResponse])
async def list_all_knowledge_bases(
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    res = await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()))
    return list(res.scalars().all())


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    res = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = res.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.post("/knowledge-bases/{kb_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    kb_id: str,
    payload: DocumentIngestRequest,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    try:
        doc = await RAGPlatformService.ingest_document(
            db=db,
            knowledge_base_id=kb_id,
            title=payload.title,
            content=payload.content,
            source_uri=payload.source_uri or "manual_upload",
            user_id=user.user_id,
        )
        return doc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/knowledge-bases/{kb_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    res = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id).order_by(KnowledgeDocument.created_at.desc())
    )
    return list(res.scalars().all())


@router.post("/knowledge-bases/{kb_id}/query", response_model=QueryResponse)
async def query_knowledge_base(
    kb_id: str,
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    results = await RAGPlatformService.query_knowledge_base(
        db=db,
        knowledge_base_id=kb_id,
        query=payload.query,
        top_k=payload.top_k,
        min_score=payload.min_score,
    )
    return QueryResponse(
        query=payload.query,
        knowledge_base_id=kb_id,
        results=[RetrievalChunk(**r) for r in results],
    )
