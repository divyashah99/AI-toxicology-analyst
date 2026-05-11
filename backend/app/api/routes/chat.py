"""Chat endpoint: RAG-style Q&A over uploaded papers, with streaming."""
from fastapi import APIRouter, Depends, Request
from starlette.responses import StreamingResponse

from app.api.deps import get_mcp
from app.api.sse import sse_format
from app.core.ratelimit import limiter
from app.mcp_client.client import McpClient
from app.models.schemas import ChatRequest, TraceEvent
from app.services import llm

router = APIRouter()


_SYS = """\
You answer questions about toxicology and chemistry strictly from the provided
context chunks. Cite sources inline as [n] referencing the chunk numbers below.
If the context does not answer the question, say so.
"""


def _format_context(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"[{i + 1}] (paper {c['paper_id'][:6]}, p.{c['page']})\n{c['text'][:700]}"
        for i, c in enumerate(chunks)
    )


@router.post("/stream")
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    body: ChatRequest,
    mcp: McpClient = Depends(get_mcp),
) -> StreamingResponse:
    user_msg = next(
        (m.content for m in reversed(body.messages) if m.role == "user"), ""
    )

    async def gen():
        # 1. retrieval (only if user supplied paper_ids OR there's a corpus)
        chunks: list[dict] = []
        if user_msg:
            res = await mcp.call(
                "papers",
                "retrieve",
                {"question": user_msg, "paper_ids": body.paper_ids or None, "k": 6},
            )
            chunks = res.get("chunks", [])
            yield sse_format(
                "tool_result",
                TraceEvent(
                    kind="tool_result",
                    label="papers.retrieve",
                    server="papers",
                    tool="retrieve",
                    output={"n": len(chunks)},
                ).model_dump(mode="json"),
            )

        ctx = _format_context(chunks) if chunks else "(no relevant context found)"

        history = [{"role": "system", "content": _SYS}]
        for m in body.messages[:-1]:
            history.append({"role": m.role, "content": m.content})
        history.append(
            {
                "role": "user",
                "content": f"CONTEXT:\n{ctx}\n\nQUESTION:\n{user_msg}",
            }
        )

        async for delta in llm.stream(history, max_tokens=700):
            yield sse_format("delta", {"text": delta})

        yield sse_format(
            "citations",
            {
                "citations": [
                    {
                        "n": i + 1,
                        "paper_id": c["paper_id"],
                        "page": c["page"],
                        "snippet": c["text"][:240],
                    }
                    for i, c in enumerate(chunks)
                ]
            },
        )
        yield sse_format("end", {"ok": True})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
