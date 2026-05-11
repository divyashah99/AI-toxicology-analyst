"""SlowAPI rate limiter wired against client IP."""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

_settings = get_settings()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{_settings.rate_limit_per_min}/minute"],
)
