**This repository is not maintained**

This code is provided as-is under its licence, with no maintainer. Vulnerability
reports will not be received, triaged or fixed. Anyone who deploys or forks this
code is solely responsible for its security, including keeping dependencies
patched.

# gaia-backend

Orchestrator for the GAIA platform — a REST API, job queue and task scheduler
that turns aerial imagery into vector map data.

## What GAIA is

An operator selects an area in QGIS and picks which object types to detect —
buildings, roads, vegetation. GAIA fetches the imagery from a WMS, runs semantic
segmentation over it, vectorises the result, and returns a GeoPackage that loads
back into QGIS as map layers.

It is built to be self-hosted by an organisation that owns or licenses its own
imagery, typically a municipality.

GAIA is three repositories:

| Repository | Role |
|---|---|
| **gaia-backend** (this one) | REST API, database, scheduling. Runs as a service. |
| **gaia-engine** | The processing: tiling, segmentation, vectorisation, comparison. Runs as subprocesses. |
| **gaia-client** | QGIS plugin. The user interface. |

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for how they fit together —
it is the canonical description and the other two repositories link to it.

## Getting started

| I want to… | Go to |
|---|---|
| Install and run GAIA on a server | [docs/INSTALLATION.md](docs/INSTALLATION.md) |
| Operate, upgrade or troubleshoot it | [docs/OPERATIONS.md](docs/OPERATIONS.md) |
| Secure it before exposing it | [SECURITY.md](SECURITY.md) |
| Integrate with the API | [docs/API.md](docs/API.md) |
| Understand the design | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Add a segmentation model or engine step | [docs/INTERFACES.md](docs/INTERFACES.md) |
| Know what is missing and what to build next | [docs/FUTURE_WORK.md](docs/FUTURE_WORK.md) |
| Work on the backend itself | Below |

> **Before exposing this to a network**, read [SECURITY.md](SECURITY.md). GAIA
> requires an API key, has no user accounts, and executes engine code on the
> host.

## Development

### Requirements

Python 3.12 and [uv](https://github.com/astral-sh/uv). To install uv:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Setup

```bash
uv sync                 # install dependencies from uv.lock
cp .env.template .env   # then fill it in
```

`.env` needs at least `POSTGRES_*`, `MODEL_BASE_PATH`, `STORAGE_PATH`, `DEBUG`
and `GAIA_API_KEY`. The application will not start without them — generate a key
with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

> `config.py` reads `env_file="../.env"`, resolved relative to the working
> directory. Start the app from the `app/` folder, or supply the environment
> directly (as Docker does).

Add a dependency with `uv add <package>` rather than `pip install`.

### Running

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Omit `--reload` if you need to run engine subprocesses — the reloader interferes
with them.

Interactive API docs are at `/docs`, and require the `X-API-Key` header like
every other endpoint except `/status/ping`.

### Testing

```bash
uv run pytest -sv
```

Tests are discovered as `*_test.py` or `test_*.py`, with functions prefixed
`test_`. The `set_env` fixture in `app/test/conftest.py` supplies the required
configuration.

### Linting

Ruff handles linting and formatting. Install the VS Code extension from the
workspace recommendations; formatting runs on save. There is no CI lint gate.

### Database migrations

[Alembic](https://alembic.sqlalchemy.org/), run from the `app/` folder:

```bash
alembic upgrade head                      # apply
alembic downgrade -1                      # roll back one revision
alembic revision -m "what this changes"   # new (empty) migration
```

New migration files are empty and must be written by hand. **Do not use
`--autogenerate`** — the PostGIS extension makes it emit conflicting results.

In Docker, migrations run automatically at container start via the compose
`post_start` hook.

### Docker

```bash
cd docker
docker compose -f linux.docker-compose.yml up --build -d
```

Full setup — folders, environment, models — is in
[docs/INSTALLATION.md](docs/INSTALLATION.md).

## License

Copyright 2024-2026 Decerno AB

Licensed under the **Apache License, Version 2.0** ([LICENSE](LICENSE)).

You may not use this file except in compliance with the License. Unless required
by applicable law or agreed to in writing, software distributed under the
License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
ANY KIND, either express or implied.

Note that `gaia-client` is licensed **GPL-3.0-or-later** — it is a QGIS plugin
and therefore a derivative work of QGIS. The two are separate works: this
backend communicates with the plugin over HTTP, which does not create a
derivative work.

Please check the licence of any new dependency before adding it. Copyleft
licences (GPL, AGPL) are incompatible with Apache-2.0 distribution and must not
be introduced here.

## Further reading

| Document | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, pipeline, tiling parameters, storage |
| [docs/API.md](docs/API.md) | Endpoint reference, auth, schemas, status codes |
| [docs/INTERFACES.md](docs/INTERFACES.md) | The engine contract and how to add one |
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | First-time server install |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Upgrades, backup, troubleshooting |
| [docs/DATABASE.md](docs/DATABASE.md) | Schema and entities |
| [docs/TASKS.md](docs/TASKS.md) | Task and step model |
| [docs/OUTPUT.md](docs/OUTPUT.md) | Result structure |
| [docs/FUTURE_WORK.md](docs/FUTURE_WORK.md) | Remaining UX gaps, engineering debt, roadmap |
| [SECURITY.md](SECURITY.md) | Hardening and safe deployment |

## Troubleshooting

If environment changes appear not to take effect, restart your terminal — stale
values persist in the shell.

Everything else is in [docs/OPERATIONS.md](docs/OPERATIONS.md).
