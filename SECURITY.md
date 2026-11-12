# Security policy

## Reporting a vulnerability

**This repository is not maintained**

This code is provided as-is under its licence, with no maintainer. Vulnerability
reports will not be received, triaged or fixed. Anyone who deploys or forks this
code is solely responsible for its security, including keeping dependencies
patched.

# Security and safe deployment

Read this before putting GAIA on a network. It is written for whoever installs
and runs the system, not for developers.

GAIA processes aerial imagery and stores the results. Anyone who can reach the
API can create projects, start processing runs, and download every result the
system holds. Treat it as a system that must be protected, not a read-only map
viewer.

---

## 1. Set an API key (required)

The backend will **not start** without `GAIA_API_KEY`. This is deliberate. There
is no default value, because a default would mean every installation shares the
same password.

Generate one:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Put it in `docker/gaia.env`:

```
GAIA_API_KEY=<the generated value>
```

Enter the **same value** in QGIS under **Inställningar → API-nyckel** in the GAIA
plugin. The plugin sends it with every request; without it the server answers
`401 Unauthorized`.

Keep `docker/gaia.env` and `docker/geoserver.env` readable by their owner only
(`chmod 600`; `docker/check_permissions.sh` verifies this). Credentials are
injected when the containers start and are not baked into the image. If you ran
an image built from an older version of this repository, rebuild with
`--no-cache` and rotate every credential.

Treat this value like a password. Do not email it, do not put it in a ticket,
and do not commit it to Git. `docker/gaia.env` is already excluded from Git.

## 2. Set a GeoServer admin password

`docker/geoserver.env` ships with `GEOSERVER_ADMIN_PASSWORD=` empty. Set it
before first start. If you leave it empty the GeoServer image falls back to its
own well-known default password, which is publicly documented and will be found
by automated scanners.

The compose files enforce this: a `geoserver-preflight` step stops GeoServer from
starting while the password is empty, a known default, or shorter than 12
characters.

## 3. Do not expose the server to the internet

By default the stack publishes:

| Port | Service | Who needs it |
|---|---|---|
| 8443 | GAIA API over HTTPS (Caddy proxy) | QGIS workstations |
| 9600 | GeoServer | QGIS workstations |
| 8000 | GAIA API, plain HTTP | **nobody** - restricted to the server itself |
| 5432 | PostgreSQL | **nobody** - restricted to the server itself |

Ports 8443 and 9600 are published on **all network interfaces**. That is fine on
an internal municipal network. It is **not** safe on a public IP address.

If the server has a public IP, do at least one of:

- Restrict ports 8443 and 9600 in the firewall to the addresses your QGIS users
  connect from, or
- Require a VPN to reach the server, or
- Put an additional authenticating reverse proxy in front of it.

**Never port-forward 8443 or 9600 from a router to this server.**

## 4. The API is only served over HTTPS

Every API request carries the shared API key, so the API is published only
through the bundled Caddy proxy on port 8443 (HTTPS). The backend's own plain
HTTP port 8000 is bound to `127.0.0.1` and cannot be reached from the network.
The QGIS plugin refuses to send the key over plain HTTP to anything but a
literal private IP address.

By default the proxy issues its certificate from its own local certificate
authority; workstations trust that root once. You can use a certificate from
your organisation's CA instead. See *HTTPS certificate* in
[docs/INSTALLATION.md](docs/INSTALLATION.md).

If you ran an earlier version that served the API over plain HTTP on the
network, **rotate `GAIA_API_KEY`**: any key sent that way may have been
observed.

GeoServer (port 9600) still speaks plain HTTP. It serves map tiles and the
plugin never sends it the API key.

## 5. Keep DEBUG off

`DEBUG=false` is the default in the templates. `DEBUG=true` writes verbose
diagnostics, including database and connection details, into the logs. Only turn
it on temporarily while investigating a problem.

## 6. Keep dependencies patched

Vulnerabilities are tracked in `docs/security-fixes-260817.md` (and the matching
files in `gaia-engine` and `gaia-client`). Two rules that are easy to get wrong:

- The **GDAL pin and the Dockerfile base image must be upgraded together.**
  Changing one without the other breaks image processing. See
  `gaia-engine/docs/security-fixes-260817.md`.
- The QGIS plugin does not install its own libraries - it uses the ones inside
  QGIS. **Patching the plugin's dependencies means upgrading QGIS.** The
  supported version is QGIS 3.44 LTR or later in the 3.x series.

---

## Checklist before going live

- [ ] `GAIA_API_KEY` generated and set in `docker/gaia.env`
- [ ] Same key entered in the QGIS plugin settings
- [ ] `GEOSERVER_ADMIN_PASSWORD` set to something you chose
- [ ] `POSTGRES_PASSWORD` set to something you chose
- [ ] `DEBUG=false`
- [ ] `proxy.env` has `GAIA_SERVER_NAME` set; workstations trust the certificate
- [ ] Plugin configured with `https://<server>:8443`
- [ ] `GAIA_API_KEY` rotated if it was ever used over plain HTTP
- [ ] Ports 8443 and 9600 not reachable from the internet
- [ ] `docker/gaia.env` and `docker/geoserver.env` not committed to Git
- [ ] `docker/check_permissions.sh` passes (credential files mode 600)

---

## Known limitations

Be aware of these when deciding how to deploy:

- **A single shared API key.** There are no user accounts, roles, or per-user
  audit trail. Everyone with the key has full access. Rotating it means updating
  every QGIS client.
- **No rate limiting.** A client can start unlimited processing runs.
- **No transport encryption by default** (see section 4).

These are acceptable for a trusted internal network. They are not sufficient for
exposing GAIA directly to the public internet.
