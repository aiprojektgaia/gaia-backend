# Security fixes — audit 2026-08-17

Remediation of `vulnerability_audit_260817.json` (OWASP Dependency-Track 4.14.1
/ Trivy). The audit reported **36 vulnerabilities across 10 packages**. All are
resolved; the resolved lock file reports zero known advisories against OSV.

## How the fixes are pinned

Only three of the affected packages are direct dependencies (`pytest`,
`python-dotenv`, `ruff`). The rest arrive transitively through
`fastapi[standard]` and `alembic`, so they are floored with
`[tool.uv] constraint-dependencies` in `pyproject.toml` rather than being
promoted to direct dependencies. A constraint applies a minimum version
*without* adding the package to the dependency graph, so the manifest keeps
saying what the project actually uses.

Re-resolve after editing:

```bash
uv lock --python 3.12
uv sync --python 3.12
```

## Resolved

| Package | Was | Now | Advisories | Worst |
|---|---|---|---|---|
| h11 | 0.14.0 | 0.16.0 | GHSA-vqfr-h8mv-ghfj, CVE-2025-43859 | critical |
| starlette | 0.48.0 | 1.6.0 | CVE-2025-62727 + 6 more | high |
| urllib3 | 2.5.0 | 2.7.0 | CVE-2026-21441, CVE-2025-66418, CVE-2025-66471 + 4 | high |
| python-multipart | 0.0.20 | 0.0.32 | CVE-2026-24486, CVE-2026-40347 + 7 | high |
| mako | 1.3.5 | 1.4.1 | CVE-2026-41205 + 2 | high |
| idna | 3.10 | 3.18 | GHSA-65pc-fj4g-8rjx | medium |
| pytest | 8.3.3 | 9.1.1 | CVE-2025-71176, GHSA-6w46-j5rx-g56g | medium |
| python-dotenv | 1.0.1 | 1.2.3 | CVE-2026-28684, GHSA-mf9w-mj56-hr94 | medium |
| ruff | 0.7.1 | 0.16.3 | CVE-2025-13327 (see note) | medium |
| pygments | 2.18.0 | 2.21.0 | GHSA-5239-wwwm-4pmq, CVE-2026-4539 | low |

Two further items were found by OSV but were **not** in the August audit, and
are fixed here as well:

| Package | Was | Now | Issue |
|---|---|---|---|
| click | 8.1.7 | 8.4.2 | PYSEC-2026-2132 — command injection in `click.edit()` |
| anyio | 4.6.2 | 4.14.2 | not a CVE; 4.6.2 was **yanked** (shipped 4.5.2 code mistagged) |

## Notes

**`ruff` / CVE-2025-13327.** The audit attributes this to `ruff`, but the
advisory text describes a ZIP parsing-differential flaw in **uv**, a different
Astral tool. OSV does not consider any `ruff` version affected. `ruff` was
upgraded regardless, since it is a dev-only tool and the bump is free. If the
build environment installs `uv` itself, ensure it is >= 0.9.6 separately — that
is outside this project's manifest.

**`starlette` 0.48 -> 1.6 is a major upgrade.** It was required: the Range-header
DoS (CVE-2025-62727) is fixed in the 1.x line for this dependency graph. FastAPI
0.141.1 declares `starlette>=0.46.0` with no upper bound and is compatible.
Verified after upgrade: 33/33 tests pass, the app constructs, and all 12 routes
are served (see below). Note that FastAPI 1.x now represents included routers as
`_IncludedRouter` objects in `app.routes` instead of flattening them into
`Route` entries — code that introspects `app.routes` directly must account for
this. The OpenAPI schema is unaffected.

## Verification

```
uv run pytest -q                  ->  33 passed
GET /openapi.json                 ->  200, 12 paths
```

Routes confirmed live: `/projects`, `/projects/{project_id}`, `/runs`,
`/runs/{run_id}`, `/runs/{run_id}/download`, `/runs/{run_id}/status`,
`/run_result/{step_external_id}`, `/models/segmentation`, `/status/ping`,
`/status/verify`, `/status/interfaces`, `/status/db-pool-status`.

`/status/interfaces` returns 500 without a reachable PostgreSQL; this is
environmental and unrelated to the upgrade.

## Known unrelated issues (not introduced here, not fixed here)

- `app/config.py` sets `env_file="../.env"`, which resolves relative to the
  working directory. Running from the repository root does not find `.env`;
  it works when the process starts in `app/` or when the environment is
  supplied directly (as in Docker). Consider an absolute path anchored to
  `__file__`.
- `ruff check .` reports 295 style findings under 0.16 that 0.7 did not flag.
  No CI workflow runs ruff, so nothing is gated on this. Left untouched to keep
  this change limited to security remediation.
