"""Supabase wrapper. Falls back to a no-op in-memory store when not configured.

This keeps local dev (and the cheap free-tier demo) working without forcing
the user to set up Supabase before they can run anything.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.config import get_settings
from app.core.logging import get_logger

log = get_logger("db.supabase")


class _MemoryStore:
    def __init__(self) -> None:
        self.papers: dict[str, dict] = {}
        self.reports: dict[str, dict] = {}

    async def upsert_paper(self, meta: dict[str, Any]) -> None:
        self.papers[meta["paper_id"]] = meta

    async def list_papers(self) -> list[dict]:
        return sorted(
            self.papers.values(),
            key=lambda p: p.get("uploaded_at", ""),
            reverse=True,
        )

    async def delete_paper(self, paper_id: str) -> None:
        self.papers.pop(paper_id, None)

    async def save_report(self, report: dict) -> str:
        rid = report.get("id") or f"r-{len(self.reports) + 1}"
        self.reports[rid] = {
            "id": rid,
            "payload": report,
            "created_at": datetime.utcnow().isoformat(),
        }
        return rid

    async def get_report(self, report_id: str) -> dict | None:
        return self.reports.get(report_id)

    async def list_reports(self) -> list[dict]:
        return sorted(
            self.reports.values(),
            key=lambda r: r.get("created_at", ""),
            reverse=True,
        )

    async def delete_report(self, report_id: str) -> None:
        self.reports.pop(report_id, None)


class _SupabaseStore:
    def __init__(self, url: str, key: str) -> None:
        from supabase import create_client  # local import: heavy

        self._sb = create_client(url, key)

    async def upsert_paper(self, meta: dict[str, Any]) -> None:
        self._sb.table("papers").upsert(
            {
                "paper_id": meta["paper_id"],
                "filename": meta["filename"],
                "title": meta.get("title"),
                "pages": meta["pages"],
                "chunk_count": meta["chunk_count"],
                "uploaded_at": meta["uploaded_at"],
            }
        ).execute()

    async def list_papers(self) -> list[dict]:
        res = (
            self._sb.table("papers")
            .select("*")
            .order("uploaded_at", desc=True)
            .limit(200)
            .execute()
        )
        return res.data or []

    async def delete_paper(self, paper_id: str) -> None:
        self._sb.table("papers").delete().eq("paper_id", paper_id).execute()

    async def save_report(self, report: dict) -> str:
        res = (
            self._sb.table("reports")
            .insert({"payload": report})
            .execute()
        )
        return res.data[0]["id"] if res.data else ""

    async def get_report(self, report_id: str) -> dict | None:
        res = self._sb.table("reports").select("*").eq("id", report_id).execute()
        return (res.data or [None])[0]

    async def list_reports(self) -> list[dict]:
        res = (
            self._sb.table("reports")
            .select("id, created_at, payload")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        return res.data or []

    async def delete_report(self, report_id: str) -> None:
        self._sb.table("reports").delete().eq("id", report_id).execute()


def _build():
    s = get_settings()
    if s.supabase_url and s.supabase_service_key:
        try:
            log.info("supabase.connected")
            return _SupabaseStore(s.supabase_url, s.supabase_service_key)
        except Exception as exc:
            log.warning("supabase.init_failed", err=str(exc))
    log.info("supabase.using_memory_store")
    return _MemoryStore()


db = _build()
