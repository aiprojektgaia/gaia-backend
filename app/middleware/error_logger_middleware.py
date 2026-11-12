import logging
import traceback
from fastapi import Request

from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger()


def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    url = request.url
    logger.error(f"Request to {url} failed with {exc.status_code} {exc.detail}")
    return JSONResponse(
        content={"Internal error": exc.detail}, status_code=exc.status_code
    )


async def exception_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        # Do some logging here
        url = request.url
        logger.error(f"Error: for request to {url} failed")
        logger.error(traceback.format_exc())

        return JSONResponse(content="Something went wrong", status_code=500)


""""
async def bad_http_logger_middleware(request: Request, call_next):
    response: HTTPResponse = await call_next(request)
    if response.status_code >= 400:
        response_body = [chunk async for chunk in response.body_iterator]
        response.body_iterator = iterate_in_threadpool(iter(response_body))
        logging.error(f"response_body={response_body[0].decode()}")
    return response
"""
