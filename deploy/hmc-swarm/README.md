# HMC Swarm Deployment — Known-Good Setup

Reference for the Industrace production deployment on the HMC Docker Swarm
(air-gapped `192.168.99.x`). This captures the **currently verified-good**
state as of 2026-08-14.

## Topology

| Service            | Node             | Host:Port    | Image (registry)                  |
|--------------------|------------------|--------------|-----------------------------------|
| `industrace-nginx` | app-node-2 (.60) | `8002:443`   | `192.168.99.58:5000/nginx-alpine:latest` |
| `industrace-backend`| app-node-2 (.60) | internal     | `192.168.99.58:5000/industrace-backend:2.3.5` |
| `industrace-frontend`| app-node-2 (.60)| internal     | `192.168.99.58:5000/industrace-frontend:2.3.4` |
| `industrace-db`    | app-node-2 (.60) | internal     | `192.168.99.58:5000/postgres:15`  |

- Reachable at `https://192.168.99.60:8002` (and `.58` via swarm ingress).
- All services pinned to `node.labels.app-node-2 == true`.
- nginx config is injected as a **docker config** (not a bind mount).
- Data volumes bind to `/home/hmcadmin/docker-persistent/industrace/{db,uploads,logs}`.

## Why this repo dir exists

The live stack is deployed from `~/industrace/` **on app-node-1** (not from
this repo — that dir is not a git checkout). This directory in the repo is a
**canonical reference copy** so the known-good setup is version-controlled and
a redeploy from source can't silently drift from the running state.

## Files

- `industrace-compose.yml` — the swarm compose (services, volumes, configs).
- `industrace-nginx.conf` — nginx config with `limit_req zone=api burst=100`
  (raised from 20 on 2026-08-14 to fix `Error loading templates` caused by the
  Asset Detail page firing ~30 parallel API calls exceeding burst=20).
- `industrace-ssl-cert.pem` / `industrace-ssl-key.pem` — NOT committed
  (self-signed, in `.gitignore`); must exist on the node for `docker config create`.

## Secrets (env vars)

The compose uses `${VAR}` placeholders. Provide values via a `.env` file next
to the compose (or export) before `docker stack deploy`:

```
DB_PASSWORD=...
SECRET_KEY=...
ENCRYPTION_KEY=...      # Fernet key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SETUP_TOKEN=...
```

## Deploy / update procedure

Because the internet node can't reach the registry (port 5000 closed, only
SSH/22 open), image pushes use: `docker save` → `scp` → `docker load` → `docker push`
via app-node-1.

```bash
# 1. Build image locally on internet node (dev repo)
docker build -t industrace-backend:<ver> -f backend/Dockerfile backend/
docker save industrace-backend:<ver> | gzip > /tmp/be.tar.gz
scp /tmp/be.tar.gz hmcadmin@192.168.99.58:/tmp/
ssh hmcadmin@192.168.99.58 \
  'gunzip -c /tmp/be.tar.gz | docker load && \
   docker tag industrace-backend:<ver> 192.168.99.58:5000/industrace-backend:<ver> && \
   docker push 192.168.99.58:5000/industrace-backend:<ver>'

# 2. Update service on manager
ssh hmcadmin@192.168.99.58 \
  'docker service update --image 192.168.99.58:5000/industrace-backend:<ver> --force industrace_industrace-backend'
```

### Full stack (re)deploy from this reference

```bash
# On app-node-1 (has the compose + ssl files + registry access)
cd ~/industrace
# ensure docker configs exist for nginx.conf / ssl (config names in compose `configs:` block)
docker config create industrace_nginx_conf_v3 ./industrace-nginx.conf
docker config create industrace_ssl_cert ./industrace-ssl-cert.pem
docker config create industrace_ssl_key ./industrace-ssl-key.pem
docker stack deploy -c industrace-compose.yml industrace
```

## nginx rate-limit note (important)

The Asset Detail page issues **~30 parallel API calls** on load. The nginx
`api` zone **must** allow a burst ≥ the number of parallel calls, else random
requests (e.g. `GET /api/print/templates`) get **503** and the frontend shows
`Error loading templates`. Known-good: `limit_req zone=api burst=100 nodelay`.
Keep `rate=50r/s` (per-IP sustained) but raise `burst` if the page grows more
parallel fetches.
