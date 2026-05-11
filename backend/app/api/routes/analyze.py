"""Analyze endpoints — both streaming (SSE) and one-shot JSON."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import StreamingResponse

from app.agent.orchestrator import AgentError, Orchestrator
from app.agent.trace import TraceBus
from app.api.deps import get_mcp
from app.api.sse import sse_format
from app.core.logging import get_logger
from app.core.ratelimit import limiter
from app.db.supabase import db
from app.mcp_client.client import McpClient
from app.models.schemas import AnalyzeRequest, AnalyzeResponse, TraceEvent

log = get_logger("api.analyze")


async def _persist_report(report) -> None:
    """Best-effort save. We never fail the request because storage is down."""
    try:
        await db.save_report(report.model_dump(mode="json"))
    except Exception as exc:
        log.warning("report.save_failed", err=str(exc))

router = APIRouter()


@router.get("/servers")
async def list_servers(mcp: McpClient = Depends(get_mcp)) -> dict:
    return {"servers": mcp.list_servers()}


@router.post("", response_model=AnalyzeResponse)
@limiter.limit("10/minute")
async def analyze(
    request: Request,
    body: AnalyzeRequest,
    mcp: McpClient = Depends(get_mcp),
) -> AnalyzeResponse:
    """One-shot JSON analysis (no streaming)."""
    bus = TraceBus()
    try:
        report = await Orchestrator(mcp).run(
            query=body.query, paper_ids=body.paper_ids, bus=bus
        )
    except AgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await bus.close()
    await _persist_report(report)
    return AnalyzeResponse(report=report, trace=bus.events)


@router.post("/stream")
@limiter.limit("10/minute")
async def analyze_stream(
    request: Request,
    body: AnalyzeRequest,
    mcp: McpClient = Depends(get_mcp),
) -> StreamingResponse:
    """SSE: emits trace events live, then a final 'report' frame."""
    bus = TraceBus()

    async def runner() -> None:
        try:
            report = await Orchestrator(mcp).run(
                query=body.query, paper_ids=body.paper_ids, bus=bus
            )
            await _persist_report(report)
            await bus.emit(
                TraceEvent(
                    kind="done",
                    label="report",
                    output=report.model_dump(mode="json"),
                )
            )
        except AgentError as exc:
            await bus.emit(TraceEvent(kind="error", label="agent_error", text=str(exc)))
        except Exception as exc:  # pragma: no cover - defensive
            await bus.emit(TraceEvent(kind="error", label="server_error", text=str(exc)))
        finally:
            await bus.close()

    asyncio.create_task(runner())

    async def event_stream():
        async for ev in bus.stream():
            yield sse_format(ev.kind, ev.model_dump(mode="json"))
        yield sse_format("end", {"ok": True})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
