"""Request logging middleware."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

logger = logging.getLogger(__name__)


async def log_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Log every HTTP request."""

    start = time.perf_counter()

    response = await call_next(request)

    duration = time.perf_counter() - start

    logger.info(
        "%s %s -> %s (%.3f s)",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )

    return response