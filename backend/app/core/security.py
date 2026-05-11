"""Lightweight request validation helpers. No real auth in MVP."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import get_settings

_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


def validate_pdf_upload(file: UploadFile) -> None:
    settings = get_settings()
    if file.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF uploads accepted"
        )
    name = Path(file.filename or "").name
    if not name or not _SAFE_NAME.match(name.replace(" ", "_")):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Invalid filename"
        )
    # Size check happens during streaming write; this is the upper guard.
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds {settings.max_upload_mb} MB",
        )
