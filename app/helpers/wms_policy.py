"""Which WMS servers a project may point the engine at.

The WMS URL is user input that the engine fetches from the server's network
position, so it is checked against an operator-managed allowlist
(``GAIA_WMS_ALLOWED_ORIGINS``) both here, before anything is stored, and again
by the engine's tiler before it makes a request. The same environment variable
is inherited by the engine subprocesses, so both checks use one list.
"""

from urllib.parse import urlsplit

from app.config import get_config


def _origin(url: str) -> str | None:
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    host = parts.hostname.lower()
    host = f"[{host}]" if ":" in host else host
    port = parts.port or (443 if parts.scheme == "https" else 80)
    return f"{parts.scheme}://{host}:{port}"


def allowed_wms_origins() -> set[str]:
    raw = get_config().GAIA_WMS_ALLOWED_ORIGINS
    return {o for o in (_origin(v) for v in raw.split(",") if v.strip()) if o}


def validate_wms_url(url) -> None:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("The WMS url is missing")
    parts = urlsplit(url.strip())
    if parts.username or parts.password:
        raise ValueError("The WMS url must not contain credentials")
    origin = _origin(url)
    if origin is None or origin not in allowed_wms_origins():
        raise ValueError(
            "The WMS server is not allowed. Ask the administrator to add it to "
            "GAIA_WMS_ALLOWED_ORIGINS."
        )
