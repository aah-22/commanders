# Deploying commanders.caabi.dev

**Result:** `https://commanders.caabi.dev` → Cloudflare Tunnel `startup-tunnel` → Coolify container `commanders-web`
(nginx-unprivileged, 8080) → `/api/` proxied to `commanders-api` (FastAPI, 8081) → Postgres 16 (`commanders-db`).
Public: **no Cloudflare Access application** (confirm no existing Access app's domain pattern covers the hostname).

## 1. Coolify resource
1. **+ New Resource → Docker Compose** → GitHub App source → `aah-22/commanders`, branch `main`, Base Directory `/`.
   Name it `commanders`.
2. **Environment variables:** `POSTGRES_PASSWORD`, `POSTGRES_RO_PASSWORD` (generate both), `SEASON=2026`,
   `MLFLOW_TRACKING_URI=http://<mlflow internal ip>:5000`, `MLFLOW_EXPERIMENT=commanders`; leave the CF vars empty.
   `DATABASE_URL` / `DATABASE_URL_RO` default to the compose-internal `db` service.
3. **Deploy** (first build: Angular ~2 min, Python ~3 min). Then force-deploy without cache after every source change.
4. **Internal IP** for the tunnel. Coolify names containers `<service>-<resource id>-…` (for example
   `web-oyqrne93d7qvlhbdmmf7sbtq-…`), so filter on the service name plus the id shown in the resource's URL:
   `sudo docker ps --format '{{.Names}}' | grep -E '^(web|api|db)-'` to find it, then
   `sudo docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' $(sudo docker ps -qf name=web-<resource id>)`
5. **Scheduled Tasks** (container `commanders-api`, cron in UTC):

| Name | Command | Cron (UTC) | ET |
|---|---|---|---|
| `nightly-ingest` | `python -m ingest.run --nightly` | `10 9 * * *` | 05:10 (nflverse pbp/stats rebuild overnight) |
| `nightly-score` | `python -m models.score` | `30 10 * * *` | 06:30 |
| `weekly-train` | `python -m models.train --all` | `0 11 * * 2` | Tue 07:00 |
| `weekly-evaluate` | `python -m models.evaluate` | `30 11 * * 2` | Tue 07:30 |

One-time bootstrap from a shell in the api container (Coolify's browser terminal drops its websocket behind
Cloudflare; from an SSH session on the Droplet use `sudo docker exec -it $(sudo docker ps -qf name=api-<resource id>) sh`,
cwd `/srv`; wrap the backfill in `nohup … > /data/backfill.log 2>&1 &` if the session may drop): `alembic upgrade head` (also automatic at start),
`python -m ingest.run --full --seasons 2016-2026` (~30–45 min, per-season loop, `nflreadpy` cache on `/data`),
`python -m models.train --all`, `python -m models.score`.

## 2. Tunnel ingress
On the Droplet, above the `http_status:404` catch-all in `/etc/cloudflared/config.yml`:
```yaml
  - hostname: commanders.caabi.dev
    service: http://<web ip>:8080
```
```bash
cloudflared tunnel route dns startup-tunnel commanders.caabi.dev
sudo systemctl restart cloudflared
```
No firewall change (tunnel is outbound only). Re-run the `docker inspect` line after deploys; the IP can change.

## 3. Cloudflare rules (optional, recommended)
Cache rule: `commanders.caabi.dev/api/v1/*` → cache eligible, edge TTL 5 min (the API sets `Cache-Control` too).
Rate-limit rule on `/api/*` (e.g. 300 req/min per IP) as a second layer behind the app's own limiter.

## 4. Verify
```bash
curl -sI https://commanders.caabi.dev/healthz | head -1     # 200
curl -s  https://commanders.caabi.dev/api/ready               # {"status":"ok","database":true}
curl -s  https://commanders.caabi.dev/api/v1/meta/freshness   # season/week the data runs through
curl -s  https://commanders.caabi.dev/api/v1/season/2026/summary | head -c 400   # standing + weekly rows for WAS
```
Migrations run at API start (`0003` adds `nfl.team_game_stats`, `gm.team_game_summary`, `gm.standings` and
`plays.qb_epa`). On a database ingested before phase 2, run once from the resource terminal:
`python -m ingest.run --season 2026 --jobs plays,team_game_stats,derive` (fills `qb_epa`), then
`python -m ingest.run --full --jobs team_game_stats,derive`. The nightly run derives on its own from then on.
Loki: `{job="docker"} |= "ingest complete"`.

## 5. Ops notes
- Memory: API ≈ 200 MB idle; the one-off backfill peaks ≈ 1–1.5 GB (run it at night; `mem_limit` if needed).
- Volumes: `commanders-pgdata` (the database), `commanders-cache` (nflreadpy cache). Droplet snapshots cover both.
- MLflow unreachable → jobs still complete (tracking becomes a no-op with a one-line notice), like draft-engine.
