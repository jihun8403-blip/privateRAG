"""Documents API 라우터 (SDS §6.3)."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import DbDep
from app.api.schemas.document import DocumentRead, DocumentVersionRead
from app.models.document import Document, DocumentVersion

router = APIRouter()


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    db: DbDep,
    topic_id: Optional[str] = Query(None),
    archive_tier: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """문서 목록 조회 (주제별 필터 가능)."""
    stmt = select(Document)
    if topic_id:
        stmt = stmt.where(Document.topic_id == topic_id)
    if archive_tier:
        stmt = stmt.where(Document.archive_tier == archive_tier)
    if is_active is not None:
        stmt = stmt.where(Document.is_active == is_active)
    stmt = stmt.offset(offset).limit(limit).order_by(Document.collected_at.desc())

    result = await db.execute(stmt)
    return list(result.scalars())


@router.get("/{doc_id}", response_model=DocumentRead)
async def get_document(doc_id: str, db: DbDep):
    """문서 상세 조회."""
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    return doc


@router.get("/{doc_id}/versions", response_model=list[DocumentVersionRead])
async def list_versions(doc_id: str, db: DbDep):
    """문서 버전 이력 조회 (TC-S04)."""
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

    stmt = (
        select(DocumentVersion)
        .where(DocumentVersion.doc_id == doc_id)
        .order_by(DocumentVersion.version_no)
    )
    result = await db.execute(stmt)
    return list(result.scalars())


@router.get("/{doc_id}/versions/{version_no}", response_model=DocumentVersionRead)
async def get_version(doc_id: str, version_no: int, db: DbDep):
    """특정 버전 조회."""
    stmt = select(DocumentVersion).where(
        DocumentVersion.doc_id == doc_id,
        DocumentVersion.version_no == version_no,
    )
    version = (await db.execute(stmt)).scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=404, detail="해당 버전을 찾을 수 없습니다.")
    return version
