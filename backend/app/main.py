"""FastAPI entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from app.api.routes import analyze, chat, papers, reports
from app.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.ratelimit import limiter
from app.mcp_client.client import McpClient

settings = get_settings()
configure_logging(settings.log_level)
log = get_logger("app.main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("startup", model=settings.openai_model, provider=settings.llm_provider)
    client = McpClient()
    await client.start()
    app.state.mcp = client
    try:
        yield
    finally:
        await client.stop()
        log.info("shutdown")


app = FastAPI(
    title="AI Toxicology Analyst",
    version="0.1.0",
    description="MCP-orchestrated toxicology analysis backend",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(_, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429, content={"detail": f"Rate limit exceeded: {exc.detail}"}
    )


app.include_router(analyze.router, prefix="/api/analyze", tags=["analyze"])
app.include_router(papers.router, prefix="/api/papers", tags=["papers"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "AI Toxicology Analyst",
        "version": "0.1.0",
        "docs": "/docs",
    }
