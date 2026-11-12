"""API key authentication.

This API exposes project data and can launch processing runs, so it must not be
reachable without a credential. Every request needs an ``X-API-Key`` header
matching ``GAIA_API_KEY`` from the environment.

``GAIA_API_KEY`` is required and has no default: the application refuses to
start without it (see ``app.config.Config``). That is deliberate - a silent
fallback would mean an operator who never reads the documentation ends up
running an open API on a public interface.
"""

import logging
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import get_config

logger = logging.getLogger()

API_KEY_HEADER = "X-API-Key"

# Liveness only. Returns no data and is needed by container healthchecks and by
# the QGIS plugin's "is this URL reachable" test before a key has been entered.
PUBLIC_PATHS = frozenset({"/status/ping"})


def _is_public(path: str) -> bool:
    # Tolerate a trailing slash so "/status/ping/" is not treated as protected.
    return path.rstrip("/") in {p.rstrip("/") for p in PUBLIC_PATHS}


async def api_key_middleware(request: Request, call_next):
    if request.method == "OPTIONS" or _is_public(request.url.path):
        return await call_next(request)

    expected = get_config().GAIA_API_KEY
    provided = request.headers.get(API_KEY_HEADER)

    # compare_digest avoids leaking the key through response timing. Compare
    # bytes: on str it raises TypeError for non-ASCII input, which would turn
    # a bad header into a 500 instead of a 401.
    if not provided or not secrets.compare_digest(
        provided.encode("utf-8", "surrogateescape"), expected.encode("utf-8")
    ):
        reason = "missing" if not provided else "invalid"
        logger.warning(
            f"Rejected request to {request.url.path}: {reason} {API_KEY_HEADER}"
        )
        return JSONResponse(
            content={"detail": f"{reason.capitalize()} {API_KEY_HEADER}"},
            status_code=401,
        )

    return await call_next(request)
