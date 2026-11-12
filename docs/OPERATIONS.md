# Operations runbook

Deploying, upgrading and troubleshooting a running GAIA installation. For
first-time installation see [INSTALLATION.md](INSTALLATION.md); for hardening
before exposing it to a network see [SECURITY.md](../SECURITY.md).

All commands assume you are in `gaia-backend/docker`.

## Everyday commands

```bash
docker compose -f linux.docker-compose.yml up -d          # start
docker compose -f linux.docker-compose.yml down           # stop
docker compose -f linux.docker-compose.yml logs -f gaia   # follow backend logs
docker compose -f linux.docker-compose.yml ps             # container + port status
```

Application logs are also written to `/opt/gaia/logs` on the host (mounted as
`/opt/gaia/backend/logs`). Verbosity is controlled by `DEBUG`: `false` selects
`logging_config_info.ini`, `true` selects the far noisier `logging_config.ini`.
Keep `DEBUG=false` in production.

## Health checks

```bash
curl -s localhost:8000/status/ping                                   # no auth needed
curl -s -H "X-API-Key: $KEY" localhost:8000/status/verify | jq       # full check
curl -s -H "X-API-Key: $KEY" localhost:8000/models/segmentation | jq # selectable models
```

`/status/verify` is the first thing to run when something is wrong — it reports
`{ok, message}` for the database, migrations, engine and storage filesystems,
active interfaces, and the poller.

A healthy startup log ends with:

```
Finished scanning and installing interfaces
```

with **no** `Error setting up interface` lines above it.

## Upgrading

Which steps you need depends on what changed. Getting this wrong is the single
most common source of breakage.

| What changed | Rebuild image? | Delete interface venvs? |
|---|---|---|
| Backend Python code | **yes** | no |
| `docker/*.env` values | no — restart is enough | no |
| Engine Python code | no — it is bind-mounted | no |
| An engine `requirements.txt` | no | no *(pip re-runs each start)* |
| **Dockerfile base image** | **yes** | **yes — all of them** |

### Backend code change

```bash
git pull
docker compose -f linux.docker-compose.yml up --build -d gaia
```

Code is baked in by `COPY . /opt/gaia/backend`, so a plain `restart` runs the
old code. Environment values are read at runtime and only need a restart.

### Base image change — the dangerous one

Interface virtual environments live on the host bind-mount
(`/opt/gaia/gaia-engine/*/venv`). They **survive image rebuilds** and link
against the interpreter and native libraries of the image that created them.
Change the base image and every one of them breaks.

```bash
rm -rf /opt/gaia/gaia-engine/*/venv /opt/gaia/gaia-engine/core/*/venv
docker compose -f linux.docker-compose.yml up --build -d
```

Deleting only some of them leaves the rest broken. Expect a slow first start —
`segmentation` reinstalls `torch` via `segmentation-models-pytorch`, several GB. A long silent
startup is normal, not a hang.

### Database migrations

Migrations run automatically on container start, via the compose `post_start`
hook calling `docker/run_migrations.sh` (`alembic upgrade head`). To run them by
hand:

```bash
docker compose -f linux.docker-compose.yml exec gaia \
  sh -c "cd app && /opt/gaia/backend/.venv/bin/alembic upgrade head"
```

## Backup

Two things hold state; both are needed for a usable restore.

```bash
# 1. Database
docker compose -f linux.docker-compose.yml exec db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > gaia-$(date +%F).sql

# 2. Result files
tar czf gaia-storage-$(date +%F).tar.gz /opt/gaia/storage
```

The database stores only metadata and *paths*; the imagery and GeoPackages live
in `/opt/gaia/storage`. A database-only backup restores an installation whose
runs all point at missing files.

`/opt/gaia/pgdata` is the live database volume — back up the `pg_dump` output,
not this directory, unless the stack is stopped.

## Troubleshooting

### Backend container restarts in a loop

```
pydantic_core.ValidationError: 1 validation error for Config
GAIA_API_KEY  Field required
```

`GAIA_API_KEY` is unset in `docker/gaia.env`. This is deliberate — the backend
refuses to start rather than run unauthenticated. Generate one:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

The same error shape appears for any missing required setting (`POSTGRES_*`,
`MODEL_BASE_PATH`, `STORAGE_PATH`, `DEBUG`).

### `could not translate host name "db"`

DNS failed, not the database. Note the exact wording:

- `Temporary failure in name resolution` (`EAI_AGAIN`) — the resolver itself was
  unreachable, i.e. the process was not attached to the compose network yet.
  Usually a startup race in the `post_start` migration hook. Retry the start; if
  it persists, run the migration manually (above).
- `Name or service not known` (`EAI_NONAME`) — the hostname is genuinely wrong.
  Check `POSTGRES_SERVER` in `docker/gaia.env`; inside compose it must be `db`.

`depends_on: db` waits only for the container to be created, not for PostgreSQL
to accept connections, and the `db` healthcheck is `exit 0` — a no-op that
always reports healthy. Neither provides real ordering.

### `Interface <name> is not active or installed`

The interface's `pip install` failed at startup, and the failure handler set
both `installed = False` and `is_active = False`. Find the real cause:

```bash
docker compose -f linux.docker-compose.yml logs gaia | grep -i "Error setting up interface"
```

The log line quotes pip's actual output. Common causes:

| Message contains | Cause | Fix |
|---|---|---|
| `error while loading shared libraries: libpython3.*.so` | Stale venv from an older base image | Delete **all** interface venvs (above) |
| `gdal-config` / `gdal.h` not found | GDAL pin does not match the base image | Align the pin and the `FROM` line — see the engine notes |
| `No matching distribution` | Bad pin, or no network from the container | Fix the pin / check egress |

Interfaces recover automatically once a start succeeds — `is_active` is set back
to `true` by a successful install.

### `No steps found for Task type <X>` and the run is killed

Almost always a **downstream symptom**. A task handler produces no steps when
the preceding task has no `FINISHED` steps, or when those steps produced no
output files. Look *above* this error for the first failure in the run — often
`Interface ... is not active or installed`.

A single failure marks every remaining task in the run `KILLED`, so most
`KILLED` tasks are collateral rather than the cause.

### "Välj objektyper" is empty in QGIS

The selector renders one checkbox per model returned by
`GET /models/segmentation`. It is empty when that list is empty. Check, in
order:

```bash
curl -s -H "X-API-Key: $KEY" localhost:8000/models/segmentation
```

1. Returns `[]` → segmentation interfaces are inactive; see the interface
   section above.
2. Returns `401` → the plugin API key is wrong (see below).
3. Unreachable → the backend is down, or the plugin backend URL is wrong.

### The QGIS plugin reports errors after an upgrade

If the backend has an API key and the plugin does not, every request returns
`401`. The plugin logs `401 Unauthorized - the API key is missing or incorrect`
to the QGIS Python console. Enter the key under **Inställningar → API-nyckel**;
it must match `GAIA_API_KEY` exactly.

The plugin also requires **QGIS 3.44 LTR or later in the 3.x series**. On older
QGIS it fails to load entirely (it uses `enum.StrEnum`, which needs Python
3.11+); on QGIS 4.x it is blocked by `qgisMaximumVersion`.

### Image build fails on `psycopg2` — `pg_config executable not found`

The base image provides `libpq` at runtime but not its development files.
`libpq-dev` must be in the `apt-get install` line of the Dockerfile.

### Runs queue but never start

Only one step runs at a time across the whole server. Check whether another run
is occupying the pipeline:

```bash
curl -s -H "X-API-Key: $KEY" localhost:8000/status/verify | jq .poller
```

If the poller reports not ok, restart the backend. A step has no timeout at the
subprocess level; a genuinely stuck engine process must be killed by hand.
