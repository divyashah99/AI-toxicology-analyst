"""PDF ingest: parse → chunk → embed → store. Retrieval: query Chroma."""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from app.config import get_settings
from app.services import chroma, embeddings

_settings = get_settings()


# ----- chunking -----


def _normalize(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"-\n", "", text)          # join hyphenated line breaks
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    pages: list[tuple[int, str]],
    target_chars: int = 1800,
    overlap: int = 250,
) -> list[dict[str, Any]]:
    """Page-aware sliding window. Each chunk records source page."""
    chunks: list[dict[str, Any]] = []
    buf: list[tuple[int, str]] = []
    buf_len = 0

    def flush() -> None:
        if not buf:
            return
        text = " ".join(t for _, t in buf).strip()
        if not text:
            return
        page = buf[0][0]
        chunks.append({"page": page, "text": text})

    for page_no, page_text in pages:
        page_text = _normalize(page_text)
        if not page_text:
            continue
        # Split on paragraph boundaries when possible.
        for para in re.split(r"\n{2,}", page_text):
            para = para.strip()
            if not para:
                continue
            if buf_len + len(para) > target_chars and buf:
                flush()
                # Carry overlap forward
                tail = " ".join(t for _, t in buf)[-overlap:]
                buf = [(page_no, tail)] if tail else []
                buf_len = len(tail)
            buf.append((page_no, para))
            buf_len += len(para)
    flush()
    return chunks


# ----- ingest -----


async def ingest_pdf(path: Path, original_filename: str) -> dict[str, Any]:
    reader = PdfReader(str(path))
    pages: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            pages.append((i, page.extract_text() or ""))
        except Exception:
            pages.append((i, ""))

    chunks = chunk_text(pages)
    if not chunks:
        return {
            "paper_id": str(uuid.uuid4()),
            "filename": original_filename,
            "pages": len(pages),
            "chunk_count": 0,
            "title": None,
            "uploaded_at": datetime.utcnow().isoformat(),
        }

    paper_id = str(uuid.uuid4())
    texts = [c["text"] for c in chunks]
    vecs = await embeddings.embed_texts(texts)

    ids = [f"{paper_id}:{i}" for i in range(len(chunks))]
    metas = [
        {
            "paper_id": paper_id,
            "filename": original_filename,
            "chunk_idx": i,
            "page": c["page"],
        }
        for i, c in enumerate(chunks)
    ]
    chroma.add_chunks(ids, texts, vecs, metas)

    title = _guess_title(pages)
    return {
        "paper_id": paper_id,
        "filename": original_filename,
        "pages": len(pages),
        "chunk_count": len(chunks),
        "title": title,
        "uploaded_at": datetime.utcnow().isoformat(),
    }


def _guess_title(pages: list[tuple[int, str]]) -> str | None:
    if not pages:
        return None
    first = _normalize(pages[0][1])
    if not first:
        return None
    line = first.split("\n", 1)[0].strip()
    return line[:200] if 6 < len(line) < 220 else None


# ----- retrieval -----


async def retrieve(
    question: str, paper_ids: list[str] | None = None, k: int = 6
) -> list[dict[str, Any]]:
    if not paper_ids and chroma.count() == 0:
        return []
    qvec = await embeddings.embed_one(question)
    return chroma.query(qvec, k=k, paper_ids=paper_ids or None)


# ----- storage helpers -----


async def save_upload_stream(stream, filename: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)
    target = Path(_settings.upload_dir) / f"{uuid.uuid4().hex}_{safe}"
    target.parent.mkdir(parents=True, exist_ok=True)
    max_bytes = _settings.max_upload_mb * 1024 * 1024
    written = 0
    with target.open("wb") as f:
        while True:
            chunk = await stream.read(64 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                f.close()
                target.unlink(missing_ok=True)
                raise ValueError(f"File exceeds {_settings.max_upload_mb} MB")
            f.write(chunk)
    return target
