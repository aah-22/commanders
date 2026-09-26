# commanders — orientation for Claude Code

Public, read-only Washington Commanders front-office analytics at https://commanders.caabi.dev, built as a portfolio
piece for caabi.dev and as MLflow + DevSecOps practice. The lens is a general manager's: talent, production and
potential; how the 2025–26 acquisitions perform against their cost and their positional peers; who to target.
**No betting or odds content, ever** — the nflverse spread/total/moneyline columns are not mirrored.
Read `docs/commanders-build-guide.md` first; it is the source of truth for architecture and phases.

- `api/` FastAPI, GET-only, cached (in-process TTL + Cache-Control for Cloudflare), rate-limited per
  `CF-Connecting-IP`, CORS locked to the site; connects to Postgres as the SELECT-only `commanders_ro` role.
  Routers `meta` and `season` (`/v1/season/{season}/summary|league|games`); queries are Core selects in
  `api/queries/`, response models in `api/schemas/`. On SQLite the engine gets the same schema translation as ingest.
- `ingest/` nflverse (`nflreadpy`) → Postgres jobs (`python -m ingest.run --nightly | --full --seasons 2016-2026 |
  --season N --jobs plays,snap_counts`), idempotent upserts on nflverse keys, per-asset digests in `ops.dataset_versions`,
  dataset lineage logged to MLflow. Loaders are pure polars transforms (`ingest/loaders.py`), so tests feed synthetic
  frames through the production path. `ingest/derive/` rebuilds the `gm.*` tables per season as the last nightly job
  (`--jobs derive` alone re-derives): `team_game_summary` (offense/defense per team-game with weekly ranks) and
  `standings`. Play filters are in `ingest/derive/filters.py` — `play_type` is the base filter, never the `pass`/`rush`
  flags; `nflv_*` columns exist only to cross-check against the `nfl.team_game_stats` mirror (passing EPA is `qb_epa`).
  `tests/seed.py` is the hand-built season the derive and API tests share.
- `models/` MLflow-tracked models (experiment `commanders`, registry alias `champion`, promotion gate = beats champion
  and a naive baseline on hold-out MAE): production projection, acquisition value, position impact.
- `db/` SQLAlchemy 2.0 ORM (`db/schema.py`) + Alembic migrations (`alembic upgrade head` runs at API start).
  Schemas `nfl` (raw mirrors), `gm` (derived), `ml` (model outputs), `ops` (pipeline runs). On SQLite (tests)
  schemas collapse to plain tables.
- `web/` Angular 20 (standalone components, signals, lazy routes, ngx-echarts on `echarts/core`), served by
  nginx-unprivileged which proxies `/api/` to the API so the site is same-origin. Palette: gold `#c9a233` on `#0a0a0a`.
  ECharts is registered once in `core/echarts-setup.ts` (app config and specs both call `registerEcharts()`); every
  chart has a "Table view" twin; the season page's fixtures live in `features/season/testing/`.
- MLflow lives at https://mlflow.caabi.dev behind Cloudflare Access (`api/mlflow_auth.py`, same as draft-engine);
  on the Droplet use the internal `http://<ip>:5000` route with the CF vars empty.
- Infra conventions (from draft-engine / Anchor): Coolify Compose resource `commanders`, Coolify strips `ports:`,
  tunnel points at the web container's internal Docker IP:8080, force-deploy without cache after source changes.
- Run locally: `pip install -e ".[pipeline,models,dev]" && cp .env.example .env && pytest -q`;
  `cd web && npm ci && npx ng serve` (proxies `/api` to :8081); `npx ng lint`, `npx ng test --watch=false --browsers=ChromeHeadless`.
  In a root sandbox Chrome needs `--no-sandbox`: point `CHROME_BIN` at a wrapper script that adds it.
- Never commit `.env`; secrets come from Coolify / GitHub Actions secrets.
