# Installing GAIA

Sets up the backend, database and GeoServer with Docker Compose. Once this is
done, see [OPERATIONS.md](OPERATIONS.md) for running it and
[SECURITY.md](../SECURITY.md) before putting it on a network.

Supersedes the earlier `docker/DOCKER.md`.

## Before you start

> **Read [SECURITY.md](../SECURITY.md) first.** GAIA requires an API key, which
> you generate during this install. It has no user accounts, and the API must
> not be reachable from the public internet.
>
> **GAIA executes engine code on the host.** The backend runs scripts from
> `MODEL_BASE_PATH` as subprocesses. Only install engines you trust.

You need Docker with Compose v2, and roughly 20 GB free — the segmentation
environment pulls `torch` and the imagery adds up quickly.

## 1. Get the repositories

The backend and the engine must both be on disk; the engine is bind-mounted into
the backend container.

```bash
cd /opt/gaia
git clone <gaia-backend-url> gaia-backend
git clone <gaia-engine-url>  gaia-engine
```

## 2. Create the data folders

Compose maps these from the host. They must exist before the first start —
Docker will not create them for a bind mount.

```bash
mkdir -p /opt/gaia/storage /opt/gaia/logs /opt/gaia/pgdata \
         /opt/gaia/geoserver/data/contents /opt/gaia/geoserver/geo
```

| Folder | Holds |
|---|---|
| `/opt/gaia/storage` | Model output — tiles, masks, GeoPackages |
| `/opt/gaia/gaia-engine` | Engine code (the clone from step 1) |
| `/opt/gaia/pgdata` | PostgreSQL data files |
| `/opt/gaia/logs` | Backend logs |
| `/opt/gaia/geoserver/data/contents` | GeoServer data directory |
| `/opt/gaia/geoserver/geo` | Ortophotos GeoServer publishes |

If you put them elsewhere, update the `device:` paths in the `volumes:` section
of the compose file for your host OS.

## 3. Configure the environment

```bash
cd /opt/gaia/gaia-backend/docker
cp gaia.env.template      gaia.env
cp geoserver.env.template geoserver.env
cp proxy.env.template     proxy.env
```

Generate the API key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then edit `gaia.env`:

| Variable | Set to |
|---|---|
| `GAIA_API_KEY` | The generated value. **Required** — the backend will not start without it. |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | Credentials you choose |
| `POSTGRES_SERVER` | `db` — the compose service name, not `localhost` |
| `DEBUG` | `false` |
| `MODEL_BASE_PATH` | `/opt/gaia/engine` (the path *inside* the container) |
| `STORAGE_PATH` | `/opt/gaia/storage` |

In `proxy.env`, set `GAIA_SERVER_NAME` to the host name or IP address QGIS
users will type, e.g. `gaia.kommun.se` or `10.20.30.40`. It must match exactly:
the HTTPS certificate is issued for that name. Leave `GAIA_TLS=internal` unless
you have a certificate from your organisation's CA (see
[HTTPS certificate](#https-certificate) below).

And in `geoserver.env`, set `GEOSERVER_ADMIN_PASSWORD`. If you leave it empty the
image falls back to its own publicly documented default.

Neither file is tracked by Git, and both should stay that way.

They hold plaintext credentials, so lock them down and check:

```bash
chmod 600 gaia.env geoserver.env proxy.env   # owner only
chmod 750 /opt/gaia                   # no world access to the tree
./check_permissions.sh                # exits non-zero if a file is too open
```

On Windows, remove inherited permissions on the two files and grant access only
to the account that runs Docker.

The files are passed to the containers at run time and are **not** copied into
the image. If you built images from an earlier version of this repository
(which copied the whole folder, including these files, into an image layer),
rebuild with `docker compose build --no-cache`, delete the old images, and
**rotate** `GAIA_API_KEY`, `POSTGRES_PASSWORD` and `GEOSERVER_ADMIN_PASSWORD`.

## 4. Add the models

Segmentation checkpoints are not in the repository — they are large binaries.
Place them in `/opt/gaia/gaia-engine/segmentation/models/`, matching the paths in
`segmentation/parameters.json`:

| Class | Expected file |
|---|---|
| `buildings` | `buildings_50e.ckpt` |
| `roads` | `roads_50e.ckpt` |

Obtain these from your GAIA contact and copy them over, e.g.
`scp roads_50e.ckpt user@server:/opt/gaia/gaia-engine/segmentation/models/`.

Without them the segmentation interfaces install but every run fails at the
segmentation stage.

## 5. Start

```bash
cd /opt/gaia/gaia-backend/docker
docker compose -f linux.docker-compose.yml up --build -d
```

Use `windows.docker-compose.yml` on Windows.

**The first start is slow.** Each interface builds a virtual environment and
installs its dependencies; `segmentation` alone pulls several GB. Watch it:

```bash
docker compose -f linux.docker-compose.yml logs -f gaia
```

You are ready when the log reads `Finished scanning and installing interfaces`
with no `Error setting up interface` lines above it.

Database migrations run automatically on start.

### Without GeoServer

If you already have a WMS, start just the services you need:

```bash
docker compose -f linux.docker-compose.yml up -d db gaia proxy
```

## 6. Verify

On the server itself the API is also reachable over plain HTTP on
`localhost:8000` (bound to loopback only, never to the network):

```bash
KEY=<your GAIA_API_KEY>
curl -s localhost:8000/status/ping                                    # no auth
curl -s -H "X-API-Key: $KEY" localhost:8000/status/verify | jq
curl -s -H "X-API-Key: $KEY" localhost:8000/models/segmentation | jq
```

Then check the HTTPS endpoint QGIS users will use (`-k` skips certificate
verification for this one test; see below for trusting the certificate):

```bash
curl -sk https://<GAIA_SERVER_NAME>:8443/status/ping
```

Every component in `/status/verify` should report `ok: true`, and
`/models/segmentation` should list your classification models. An empty list
means the interfaces did not install — see [OPERATIONS.md](OPERATIONS.md).

## HTTPS certificate

QGIS users reach the API only through the HTTPS proxy on port **8443**. Every
request carries the API key, so it is never served over plain HTTP on the
network.

**With `GAIA_TLS=internal` (default)** the proxy runs its own small certificate
authority. Each workstation must trust its root certificate once. Export it
from the server:

```bash
docker compose -f linux.docker-compose.yml cp \
    proxy:/data/caddy/pki/authorities/local/root.crt gaia-root.crt
```

and distribute `gaia-root.crt` to the workstations, either:

- **QGIS only:** *Settings → Options → Authentication → Manage certificates →
  Authorities → Import*, choose the file and set trust to *Trusted*; or
- **Whole machine (Windows, e.g. through Group Policy):**
  `certutil -addstore Root gaia-root.crt`.

The root certificate lives in the `caddy_data` volume and survives restarts.
Deleting that volume creates a new CA, and every workstation has to trust the
new root again.

**With your organisation's certificate**, put `cert.pem` (full chain) and
`key.pem` in `docker/certs/`, set
`GAIA_TLS=/etc/caddy/certs/cert.pem /etc/caddy/certs/key.pem` in `proxy.env`
and restart the proxy. Workstations that already trust your CA need nothing
else.

## 7. Install the QGIS plugin

On each operator workstation, running **QGIS 3.44 LTR or later in the 3.x
series** (not QGIS 4.x):

1. Trust the GAIA certificate (see [HTTPS certificate](#https-certificate)).
2. **Plugins → Manage and Install Plugins → Install from ZIP**
3. Select `GaiaClient_<version>_<date>.zip` from the `gaia-client` release.
4. Open the plugin, go to **Inställningar**, and enter:
   - **Gaia backend URL** — `https://<GAIA_SERVER_NAME>:8443`
   - **API-nyckel** — the same `GAIA_API_KEY`
   - **GeoServer URL** — `http://<server>:9600` (optional)
5. Save. The plugin verifies both the URL and the key. A certificate error
   here means the workstation does not trust the GAIA certificate yet.

## Connecting GAIA to GeoServer

Containers on the same Docker network address each other by service name, not
`localhost`. When telling the backend where GeoServer is, use:

```
http://geoserver:8080/geoserver/wms
```

Note that this is the *internal* port (8080), not the published one (9600), and
that **the QGIS client cannot use this hostname** — workstations need the
server's external address, `http://<server>:9600/geoserver/wms`.

The backend and the engine only fetch WMS tiles from origins listed in
`GAIA_WMS_ALLOWED_ORIGINS` in `gaia.env` (default in the template:
`http://geoserver:8080`). Projects pointing anywhere else are rejected, so the
server cannot be used to probe your internal network. Add other WMS servers
there explicitly if you need them.

## Useful during setup

```bash
docker logs <container>                       # container logs
docker exec -it <container> bash              # shell inside a container
psql -U <user> -h localhost -d <db>           # database (from the host)
ssh -L 8000:localhost:8000 user@server        # tunnel to the loopback-only API
scp <file> user@server:/destination/folder    # copy files to the server
```
