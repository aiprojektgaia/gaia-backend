# Native libgdal for the whole stack. GHSA-wphc-7cm7-8mf7 (stack buffer overflow
# in the netCDF driver) affects libgdal 3.1.0 through 3.13.0, so this must stay
# >= 3.13.1. The GDAL pin in gaia-engine/core/image_bitter/requirements.txt has
# to match this version exactly - the engine rebuilds that interface's venv from
# an sdist on every start, and a mismatch fails the build.
FROM ghcr.io/osgeo/gdal:ubuntu-small-3.13.2

RUN apt-get -y update
# python3-dev, not python3.12-dev: the GDAL base images track their Ubuntu
# release (24.04 -> 26.04), so the default Python version moves with them and a
# hardcoded minor version stops resolving.
# libpq-dev provides pg_config, which psycopg2 needs to build from source. The
# GDAL images link against libpq at runtime but do not ship its development
# files, so this must be installed explicitly.
RUN apt-get -y install build-essential libssl-dev python3-dev libpq-dev
RUN apt-get -y install libgl1 libglx-mesa0 libglib2.0-0

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy only what the application needs - an explicit allowlist, never `COPY .`.
# Runtime credentials (docker/gaia.env etc.) must not end up in an image layer;
# they are injected at run time through `env_file` in the compose file.
# .dockerignore is a second line of defence.
COPY pyproject.toml uv.lock README.md .python-version /opt/gaia/backend/
COPY app /opt/gaia/backend/app
COPY --chmod=755 docker/run_migrations.sh /opt/gaia/backend/docker/run_migrations.sh

#CMD ["/bin/ls", "-l", "/app"]
WORKDIR /opt/gaia/backend

RUN uv sync --frozen --no-cache

# Run the application.
#CMD ["/opt/gaia/backend/.venv/bin/fastapi", "run", "app/main.py", "--port", "8000", "--host", "0.0.0.0"]

WORKDIR /opt/gaia/backend

CMD ["/opt/gaia/backend/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]