"""Report listing/retrieval/delete."""
from fastapi import APIRouter, HTTPException, status

from app.db.supabase import db

router = APIRouter()


@router.get("")
async def list_reports() -> dict:
    rows = await db.list_reports()
    return {"reports": rows}


@router.get("/{report_id}")
async def get_report(report_id: str) -> dict:
    row = await db.get_report(report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return row


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: str) -> None:
    await db.delete_report(report_id)
