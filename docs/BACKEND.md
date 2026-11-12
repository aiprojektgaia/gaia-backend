# Backend internals

How the application is wired together. For the system-level view see
[ARCHITECTURE.md](ARCHITECTURE.md).

## Layering

Code is separated into four layers, outermost first:

| Layer | Directory | Responsibility |
|---|---|---|
| **Routes** | `app/routes/` | HTTP only — parse, validate, delegate. No business logic. |
| **Use cases** | `app/usecase/` | One user-facing operation each, e.g. `create_project_run`. Orchestrates services. |
| **Services** | `app/service/` | Domain logic spanning entities: `dispatcher`, `interface_service`, `model_service`. |
| **Repositories** | `app/repository/` | Database access. The only layer that builds queries. |

The rule that matters: **a layer may call inwards, never outwards.** A
repository must not import a service. Keeping queries inside repositories is
what makes services testable with a mocked session.

## Dependency injection

Wiring uses [dependency-injector](https://python-dependency-injector.ets-labs.org/).
`app/container.py` declares every component and how to build it; routes receive
what they need through FastAPI's `Depends`:

```python
@router.get("/segmentation", response_model=List[ModelPublic])
@inject
def get_segmentation_models(
    model_service: ModelService = Depends(Provide[Container.model_service]),
) -> list[ModelPublic]:
    ...
```

Repositories are given a session per request rather than holding one, via
`set_session()`. Services receive a `session_factory` and open a session inside
a `with` block, which is what keeps sessions short-lived and returned to the
pool.

`Container` is also attached to the app (`fast_app.container = container`) so
background tasks can resolve components outside a request.

## Middleware

Applied outermost first — note that Starlette runs middleware in reverse order
of registration, so the API key check added *last* runs *first*:

1. `api_key_middleware` — rejects unauthenticated requests with `401` before any
   route or handler runs.
2. `exception_handling_middleware` — catches anything unhandled, logs the
   traceback, returns an opaque `500`.
3. `CORSMiddleware` — only added when `CORS_ALLOW_ORIGINS` is set.

## Background processing

`lifespan` in `app/main.py` starts `poll_queue` as an asyncio task at startup and
signals it to stop at shutdown. The poller drives the dispatcher; see
[TASKS.md](TASKS.md) and [ARCHITECTURE.md](ARCHITECTURE.md).

`app/system_state.py` holds process-wide flags — whether interfaces finished
installing, for instance — which `/status/verify` reports.

## Configuration

`app/config.py` defines a single pydantic-settings `Config`, cached with
`lru_cache` so it is parsed once. Fields declared `Field(...)` are required and
the application refuses to start without them — deliberate for `GAIA_API_KEY`,
so an installation cannot accidentally run unauthenticated.
