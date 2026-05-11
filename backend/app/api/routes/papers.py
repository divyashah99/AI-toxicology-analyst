"""Paper upload, list, delete."""
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.api.deps import get_mcp
from app.core.ratelimit import limiter
from app.core.security import validate_pdf_upload
from app.db.supabase import db
from app.mcp_client.client import McpClient
from app.services import chroma, papers

router = APIRouter()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
@limiter.limit("6/minute")
async def upload(
    request: Request,
    file: UploadFile = File(...),
    mcp: McpClient = Depends(get_mcp),  # noqa: ARG001 - reserved for future per-tenant scoping
) -> dict:
    validate_pdf_upload(file)
    try:
        path = await papers.save_upload_stream(file, file.filename or "upload.pdf")
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    meta = await papers.ingest_pdf(path, file.filename or path.name)

    # Best-effort persist; Supabase is optional
    try:
        await db.upsert_paper(meta)
    except Exception:
        pass

    return meta


@router.get("")
async def list_papers() -> dict:
    rows = await db.list_papers()
    return {"papers": rows, "chunks_indexed": chroma.count()}


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(paper_id: str) -> None:
    chroma.delete_paper(paper_id)
    try:
        await db.delete_paper(paper_id)
    except Exception:
        pass
