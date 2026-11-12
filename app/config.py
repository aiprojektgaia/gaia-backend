from functools import lru_cache
import logging
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    PROJECT_NAME: str = "Gaia - Papagaia"
    PROJECT_VERSION: str = "1.0.0"

    POSTGRES_USER: str = Field(...)
    POSTGRES_PASSWORD: str = Field(...)
    POSTGRES_SERVER: str = Field(...)
    POSTGRES_PORT: str = Field(...)
    POSTGRES_DB: str = Field(...)

    DB_POOL_SIZE: int = Field(default=20)
    DB_MAX_OVERFLOW: int = Field(default=30)
    DB_POOL_TIMEOUT: int = Field(default=300)
    DB_POOL_RECYCLE: int = Field(default=3600)

    @property
    def get_database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    DEBUG: bool = Field(...)
    MODEL_BASE_PATH: str = Field(...)
    STORAGE_PATH: str = Field(...)

    # Shared secret required in the X-API-Key header on every request.
    # Required on purpose - no default. The application will not start without
    # it, so an operator cannot accidentally run an unauthenticated API on a
    # public interface. Generate one with: python -c "import secrets;
    # print(secrets.token_urlsafe(32))"
    GAIA_API_KEY: str = Field(..., min_length=16)

    # Comma-separated browser origins allowed to call this API, e.g.
    # "https://gis.example.se,https://kartor.example.se".
    # Empty (the default) disables cross-origin browser access entirely. The
    # QGIS plugin is unaffected either way - it is not a browser, so CORS does
    # not apply to it. Never set this to "*": combined with credentials that
    # lets any website call this API from a visitor's browser.
    CORS_ALLOW_ORIGINS: str = Field(default="")

    @property
    def cors_allow_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ALLOW_ORIGINS.split(",")
            if origin.strip() and origin.strip() != "*"
        ]

    TASK_STEP_TIMEOUT_SECONDS: int = Field(default=1800)

    # WMS servers projects may use, as comma-separated origins
    # (scheme://host:port). Also read by the engine's tiler, which inherits
    # this environment. Default: the GeoServer shipped with GAIA.
    GAIA_WMS_ALLOWED_ORIGINS: str = Field(
        default="http://localhost:9600,http://127.0.0.1:9600"
    )

    # Each interface id in a run creates its own task; keep the fan-out small.
    MAX_INTERFACES_PER_RUN: int = Field(default=10)

    # Result download limits. The archive is built in a temporary file (never
    # in memory) and refused beyond these bounds.
    DOWNLOAD_MAX_FILES: int = Field(default=5000)
    DOWNLOAD_MAX_BYTES: int = Field(default=20 * 1024**3)
    DOWNLOAD_MAX_CONCURRENT: int = Field(default=2)
    # A download still streaming after this long is cut off and its slot freed.
    # Idle (stalled-client) timeouts belong in the reverse proxy.
    DOWNLOAD_MAX_SECONDS: int = Field(default=2 * 60 * 60)

    DEFAULT_IMAGE_TILER_INTERFACE_NAME: str = Field(default="wms_tiler")
    DEFAULT_IMAGE_TO_BIT_INTERFACE_NAME: str = Field(default="image_bitter")
    DEFAULT_VECTORIZE_INTERFACE_NAME: str = Field(default="vector_hector")

    # Required to load from .env file
    model_config = SettingsConfigDict(env_file="../.env")


logger = logging.getLogger()


def get_callback_url(task_id: str):
    # TODO: See if there's a way to get the callback_url from uvicorn or similar
    return f"http://localhost:8000/run_result/{task_id}"


@lru_cache
def get_config():
    return Config()
