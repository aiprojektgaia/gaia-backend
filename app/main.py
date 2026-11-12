# Copyright 2024-2026 Decerno AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import uvicorn

from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_config
from app.container import Container
from app.log_setting.log_setup import setup_logs
from app.middleware.api_key_middleware import api_key_middleware
from app.middleware.error_logger_middleware import (
    exception_handling_middleware,
)
from app.routes.project import router as project_router
from app.routes.interface import router as interface_router
from app.routes.project_run import router as project_run_router
from app.routes.run_result import router as run_result_router
from app.routes.status import router as system_status_router
from app.tasks.poller import poll_queue

description = """
Backend for the Gaia platform. Allows you to execute models on geographic data in order to segment and classify the data.
"""


@asynccontextmanager
async def lifespan(local_app: FastAPI):
    stop_event = asyncio.Event()
    polling_task = asyncio.create_task(poll_queue(stop_event, enabled=True))
    yield
    stop_event.set()
    await polling_task


def create_app() -> FastAPI:
    setup_logs()
    container = Container()
    db = container.db()

    interface_service = container.interface_service()
    interface_service.scan_and_install_interfaces()

    fast_app = FastAPI(
        lifespan=lifespan,
        title="Gaia Backend",
        description=description,
        summary="Gaia is a platform for running AI models.",
        version="0.1.0",
    )
    fast_app.container = container

    # app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    fast_app.add_middleware(
        BaseHTTPMiddleware, dispatch=exception_handling_middleware
    )

    # Added after the exception handler so it runs *before* it: unauthenticated
    # requests are rejected without reaching any route or the error handler.
    fast_app.add_middleware(
        BaseHTTPMiddleware, dispatch=api_key_middleware
    )

    # Cross-origin access is opt-in via CORS_ALLOW_ORIGINS. It was previously
    # allow_origins=["*"] with allow_credentials=True - a combination the CORS
    # spec forbids, which Starlette resolves by echoing back the caller's
    # origin. That let any website issue credentialed requests to this API from
    # a visitor's browser. The QGIS plugin is not a browser and never needed
    # CORS, so leaving this unset costs no functionality.
    origins = get_config().cors_allow_origins
    if origins:
        fast_app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Include the different routes created in the app
    fast_app.include_router(project_router)
    fast_app.include_router(interface_router)
    fast_app.include_router(project_run_router)
    fast_app.include_router(run_result_router)
    fast_app.include_router(system_status_router)

    return fast_app


app = create_app()


# for debugging
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
