# commanders — build guide

*Started 2026-09-25. This is the source of truth for architecture and phases; CLAUDE.md points here. It follows the
structure of draft-engine's build guide so the two portfolio projects read the same way.*

## §0 What you are building

A public, read-only Washington Commanders front-office dashboard. Nightly nflverse ingest → Postgres → FastAPI →
Angular, with MLflow-tracked models that grade acquisitions and rank targets. **No betting or odds content.**

A public, read-only Commanders front office dashboard: nightly nflverse ingest → Postgres → FastAPI → Angular, with
MLflow-tracked models that grade acquisitions and rank targets. DevSecOps is a first-class deliverable (every CI gate
from draft-engine plus SBOM, CodeQL, secret scanning, Dependabot, signed images).

### Architecture

```
nflverse (nflreadpy)                           Coolify Compose resource `commanders` on the Droplet
 pbp · participation · player stats · snaps     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
 rosters · draft picks · contracts (OTC)   ──►  │ ingest (cron)│─►│ Postgres 16  │◄─│ api (FastAPI)│◄─ tunnel ◄─ commanders.caabi.dev
 schedules · teams · pfr adv stats · NGS        │ + models     │  │ read-only    │  │ read-only    │            │
        │                                       └──────┬───────┘  │ api user     │  └──────────────┘   web (nginx-unprivileged,
        └── MLflow (mlflow.caabi.dev): dataset lineage,│ models,   └──────────────┘                     Angular build) ◄─┘
            metrics, registry aliases `champion`       └── model_outputs table
```


## §1 Decisions

| Decision | Choice | Why |
|---|---|---|
| Repo | new `aah-22/commanders` | own CI, Sonar project and Coolify resource; keeps draft-engine's CI fast |
| Frontend | Angular 20 standalone + signals, ngx-echarts on `echarts/core` | the caabi.dev site is Angular; canvas charts handle play-level series |
| Backend | FastAPI + Postgres 16, GET-only, read-only DB role | mirrors draft-engine; least privilege on the public path |
| Data | nflverse via `nflreadpy` (pbp, participation ≤ 2025, player/team stats, snaps, rosters, depth charts, injuries, contracts, draft picks, trades, PFR adv stats, NGS) | free, versioned, well-keyed; `load_pbp` ≈ 50k plays × 372 cols per season |
| Odds | none | not a betting site: `vegas_wp`, spread, total and moneyline columns are never mirrored |
| Models | `production-projection`, `acquisition-value`, `position-impact` in MLflow, alias `champion`, gate = beats champion and a naive baseline | the GM lens needs a projection, a cost model and a need weighting |
| Access | public, no Cloudflare Access | portfolio piece; abuse handled by edge cache + rate limits |
| Deploy | one Python image (API + scheduled jobs) + nginx web + Postgres, Coolify Compose, tunnel ingress | same operational shape as fantasy.caabi.dev |

## §2 Phases and definitions of done

0. **Scaffold + CI** — repo, Angular hello page with palette, FastAPI `/health`, compose, ci.yml with all quality
   jobs green, Sonar project, Dependabot. DoD: CI green on main, `docker compose up` serves the page locally.
1. **Ingest + schema** — alembic migrations, backfill 2016–2026, nightly job, lineage in MLflow. DoD: row counts per
   table logged; `SELECT count(*) FROM nfl.plays WHERE season=2026` matches nflverse.
2. **Season dashboard** (built) — `gm.team_game_summary` + `gm.standings`, `/api/v1/season/{season}/summary|league|games`,
   the dashboard page (record strip, EPA trend vs league, league scatter, down × distance heatmap, games table).
   DoD: every team-game's nflverse-convention passing/rushing EPA matches `nfl.team_game_stats` within 0.01
   (`tests/test_derive.py`, and `REAL_PBP_DB=… pytest tests/test_derive.py` against a real ingest); warm
   `/summary` under 50 ms; the page renders 2026 through the latest complete week with league ranks.
3. **Drive & play explorer** — `/api/games/*`, the explorer page with filters. DoD: any 2026 WAS game browsable.
4. **GM views + models** — contracts/draft/rosters, `acquisitions`, `positional_need`, three MLflow models with
   promotion gate, report cards + target board pages. DoD: every 2025–26 arrival has a card; targets list has cost,
   age, projection and the run_id behind it.
5. **Hardening + deploy** — Trivy/SBOM/cosign/CodeQL/gitleaks in CI, rate limiting, headers, Coolify resource,
   tunnel, DEPLOY.md, caabi.dev link. DoD: public URL up, all CI gates enforced, runbook written.


## §3 MLflow access
`api/mlflow_auth.py` (copied from draft-engine) adds the Cloudflare Access service-token headers to every MLflow
request when `CF_ACCESS_CLIENT_ID` / `CF_ACCESS_CLIENT_SECRET` are set; on the Droplet the jobs use the internal
`http://<ip>:5000` route with both empty. Experiment `commanders`; runs are told apart by their `stage` tag.

## §4 Scaffold (phase 0, done)
`pyproject.toml` (extras `pipeline`, `models`, `dev`; ruff `E,F,I,B,UP,S`, line length 120), `api/` with `/health`,
`/ready`, `/v1/meta/freshness` (cached, `Cache-Control`), slowapi limiter keyed on `CF-Connecting-IP`, CORS
`GET/HEAD` only; `db/schema.py` + Alembic (`0001_phase0`: `ops.pipeline_runs`, `nfl.games`); `web/` Angular
workspace with the palette, lazy routes (`/season`, `/explorer/:gameId`, `/gm/acquisitions`, `/gm/targets`,
`/players/:id`), `ApiService`, `FreshnessBanner`, `StatTile`, ECharts theme; nginx config with security headers;
Dockerfiles; `docker-compose.yml`; `db/init/01_roles.sql` (SELECT-only `commanders_ro`); CI (`quality-python`,
`quality-web`, `config-scan`, `gitleaks`, `sonar`, `images` with Trivy + CycloneDX SBOM, `deploy`), CodeQL,
Dependabot.

## §5 Data model and ingest (phase 1, built)

Implemented as `ingest/sources.py` (asset → release URL, natural key, kept columns), `ingest/loaders.py` (pure
polars transforms, unit-tested on synthetic frames), `ingest/upsert.py` (`INSERT … ON CONFLICT DO UPDATE` in 5k-row
chunks; SQLite for tests), `ingest/lineage.py` (MLflow no-op-when-unreachable tracker, a `log_input` dataset per
source) and `ingest/run.py` (`--nightly` | `--full --seasons 2016-2026` | `--season N --jobs a,b`). Tables live in
`db/schema.py` (`MIRRORS`), migration `0002`. Each asset's digest is kept in `ops.dataset_versions`, so an unchanged
file is skipped and still logged; a missing asset (not published yet) is logged as a failed job without sinking the
run. Design notes that shaped it:

Raw mirrors (idempotent upserts keyed as nflverse keys them): `games` (schedules; game_id), `plays` (pbp; game_id,
play_id — ~50k rows/season, index on (season, posteam), (season, defteam)), `participation` (offense/defense personnel
per play), `player_game_stats` (player_id, season, week), `snaps` (pfr_player_id → gsis, game), `rosters_weekly`,
`draft_picks`, `contracts` (OTC: player, team, apy, guaranteed, years, per-season cap hits, is_active),
`players` (ids crosswalk from load_ff_playerids + rosters), `teams`.
Derived (`ingest/derive/`, rebuilt per season as the last `--nightly` job, delete-then-upsert inside the run's
transaction): **`gm.team_game_summary`** (built; one row per team-game: offense `off_*` and defense `def_*` = allowed
— EPA/play, success %, explosive %, pass/rush EPA, dropback success, early-down EPA, pass rate and PROE on neutral
downs, third-down conversion, red-zone TD %, sack rate, drives, points per drive, average start, turnovers, plus each
rate's denominator and the rank among the teams that played that week) and **`gm.standings`** (built; cumulative
regular-season record per team per week, bye weeks carried forward, Pythagorean win %, division/conference rank by
win % → point differential → points for — not the full NFL tie-breakers). The play filters live in
`ingest/derive/filters.py`: display metrics use `play_type in (pass, run)`, non-null EPA, no aborted snaps (kneels,
spikes and penalty no-plays are already outside that); `nflv_pass_epa` / `nflv_rush_epa` reproduce nflverse's
`stats_team` convention (`qb_epa` over pass + spike, `epa` over run + kneel incl. aborted) purely so the derive can be
cross-checked against the `nfl.team_game_stats` mirror. Later phases add `player_season_production`
(per-position production metrics + league percentiles + age), `acquisitions` (WAS arrivals since 2025: how (FA / trade /
draft / waiver), date, contract at arrival), `positional_need` (per position: starter production vs league median,
contract years left, age), `model_outputs` (model name/version, player, season, value, run_id).

### Ingest cadence
One-off backfill 2016–2026 (pbp is the heavy one; run per season with `nflreadpy` caching on the volume). Nightly
Coolify scheduled task `ingest` (05:00 ET) for the current season; weekly `derive` after Monday night; monthly
`contracts`/`draft` refresh. Each job logs a `mlflow.log_input` dataset lineage row (pattern:
draft-engine `pipeline/ingest.py:137-142`) and a summary run tagged `stage`. nflverse release timing: pbp for a
Sunday lands overnight; the job re-tries and marks `games.stats_complete`.


## §6 The GM lens: metrics and models (phase 4)

- **Production**: per position, EPA/play (QB), EPA/target & YAC/target share (WR/TE), EPA/carry & success (RB),
  pressure rate & run stop % (DL/EDGE from pfr adv stats), coverage targets/EPA allowed (DB, from participation +
  pbp), snap share; all as season-to-date value and league percentile at position.
- **Production vs cost**: production percentile minus APY percentile at position (from `contracts`) — the acquisition
  report-card headline number; plus trend by week.
- **Positional need index**: for each WAS position group, starter production percentile vs league, contract years
  remaining, age vs position aging curve → need score 0–100.
- **Models in MLflow** (experiment `commanders/2026`, registry aliases `champion`, promotion gate = beats champion and
  a naive last-season baseline on hold-out MAE):
  1. `production-next` — next-season production percentile from age, last two seasons' production, snap share, draft
     capital (gradient boosting; hold-out by season).
  2. `acquisition-value` — expected production percentile per $ of APY at signing, used to grade arrivals and to
     price targets.
  3. `target-rank` — need-weighted score for pending FAs (contract ends after this season) and productive players on
     teams ≤ .350 win %, with age, projected production, estimated cost.
- Model outputs are written to `model_outputs` nightly; the API serves them with run_id for lineage.


## §7 API
### API (FastAPI, read-only, `GET` only, cached with an in-process TTL + `Cache-Control`, `slowapi` rate limit, CORS
locked to commanders.caabi.dev; Postgres role `api_ro` with SELECT only)
Built (phase 2; nginx strips the `/api` prefix, so the FastAPI paths are `/v1/...`): `/api/v1/season/{season}/summary?team=`
(standing, per-week rows with the game date, plays-weighted season aggregate with league ranks through the last
complete week, league weekly EPA quartiles, next game, down × distance success cells), `/api/v1/season/{season}/league`
(every team's aggregate), `/api/v1/season/{season}/games?team=` (the schedule with each played game's summary).
`team` must be an upper-case 2–3 letter abbreviation (422 otherwise); an unknown season is 404. Queries are Core
selects in `api/queries/season.py` with the ≤ 32 × 18-row aggregations in Python, so SQLite and Postgres behave alike.
Planned: `/api/games/{game_id}/drives` ·
`/api/games/{game_id}/plays?down=&distance=&personnel=&rz=` · `/api/players/{id}` · `/api/players/{id}/games` ·
`/api/gm/acquisitions?season=` · `/api/gm/need` · `/api/gm/targets?position=` · `/api/models` (versions, metrics, run
links) · `/health`.


## §8 Angular pages
### Angular (v20, standalone + signals, ngx-echarts; routes = pages)
`/season` Season dashboard (built: `features/season/` — `RecordStrip` six tiles, `EpaTrendChart` offense/defense by
week over the league median and inter-quartile band with bye weeks as gaps, `LeagueScatterChart` offense vs defense
EPA with WAS highlighted and median lines, `DownDistanceHeatmap` success-rate gap to the league with thin cells
dimmed, `GameResultsTable`; every chart has a table twin under "Table view"; ECharts registered once in
`core/echarts-setup.ts` for the app and the specs; fixtures in `features/season/testing/`),
`/games/:id` Drive & play explorer (drive chart, EPA by down/distance heatmap, personnel/formation filters, play table),
`/players/:id` Player page (game log, percentiles, contract), `/gm/acquisitions` report cards (production vs cost,
sortable), `/gm/targets` target board (need index by position, ranked targets with cost/age/production), `/about`
(data lineage, model versions from `/api/models`). Palette: `#c9a233` on `#0a0a0a`, panels `#111111`.


## §9 DevSecOps, container, deploy
### DevSecOps (CI job names)
`py-quality` (ruff, bandit, pip-audit, pytest --cov, coverage to Sonar) · `web-quality` (npm ci, eslint,
`ng test --watch=false --browsers=ChromeHeadless`, `ng build`, `npm audit --audit-level=high`) · `codeql` (python +
javascript) · `secrets` (gitleaks) · `sonar` (SonarCloud with both coverage reports) · `images` (build api + web,
Trivy CRITICAL/HIGH exit 1, `trivy sbom` CycloneDX attached as artifact, cosign keyless sign) · `deploy` (Coolify
webhook, main only, gated on secret presence) · Dependabot for pip/npm/actions weekly. Runtime: non-root containers,
nginx-unprivileged with CSP/X-Frame-Options/Referrer-Policy headers, read-only DB role for the API, ingest user
separate, secrets only in Coolify.

### Deployment
`docker-compose.yml`: `web` (nginx, 8080), `api` (8000), `db` (postgres:16-alpine, named volume), ingest runs as
Coolify scheduled tasks in the `api` image (`python -m ingest.nightly`). Tunnel ingress `commanders.caabi.dev →
http://<web ip>:8080` above the 404 catch-all, `cloudflared tunnel route dns`, no Access application. Cloudflare
handles HSTS/TLS; nginx proxies `/api/` to the api service so the site is same-origin.


Deployment steps live in `docs/DEPLOY.md`.

## §10 Runbook
- Nightly: `nightly-ingest` 05:10 ET, `nightly-score` 06:30 ET; weekly `weekly-train` / `weekly-evaluate` Tue 07:00.
- Re-derive a season after a code change: `python -m ingest.run --season 2026 --jobs derive`.
- After deploying phase 2 on a database ingested before it: `python -m ingest.run --season 2026 --jobs plays,team_game_stats,derive`
  (re-ingests plays so `qb_epa` is populated; the cross-check columns stay null for seasons not re-ingested) and
  `python -m ingest.run --full --jobs team_game_stats,derive` for the earlier seasons.
- A red `nightly-ingest` is usually nflverse not having published yet: the job retries next night; the site's
  freshness banner shows the week the data runs through.

## §11 Gotchas

pbp volume (index by season/team; backfill per season); nflverse publishes pbp overnight after games (job retries,
`stats_complete` flag); `nflreadpy` function names/columns drift (pin version, contract test per dataset); OTC
contract coverage is good for veterans, thinner for UDFAs (fall back to rookie-scale by draft slot); defensive
production metrics are noisier than offensive ones (show sample sizes).

Postgres enforces `varchar(n)` and SQLite does not, so a too-narrow mirror column only fails in production: the first
backfill died on a 102-character `college_name`. Every text column in the `nfl` mirrors is therefore unbounded `Text`
(migration `0004` widened the originals); keep it that way when adding a mirror column.


Additional facts verified against `nflreadpy` 0.1.5: `load_participation` stops at 2025; `load_contracts()` `team`
is a nickname or `A/B` string and carries a nested `season_history` (unnest, drop the `Total` row); snaps, PFR
advanced stats and trades are keyed by `pfr_id` (crosswalk via `load_players`); `load_depth_charts` is daily
snapshots from 2025 (thin to one per week) but one row per team-week through 2024 (`club_code`, `depth_team`,
`depth_position`; `loaders.depth_charts_legacy` maps it); `load_pfr_advstats` raises for seasons before 2018
(`run.JOB_FIRST_SEASON` skips them); cache API is `nflreadpy.config.update_config(cache_mode=..., cache_dir=...)`.
Angular's CLI 21 needs Node ≥ 22.22.3; the project pins Angular 20 (Node 22.x) — upgrade both together.
Reconciling team EPA with nflverse (verified on all 66 2026 team-games): `stats_team.rushing_epa` is `sum(epa)` over
`play_type in (run, qb_kneel)` including aborted snaps, and `passing_epa` is `sum(qb_epa)` (not `epa`) over
`play_type in (pass, qb_spike)` — the two differ on completed passes fumbled away. The `pass`/`rush` flags include
penalty no-plays and exclude scrambles, so they are never the base filter. Three weeks in, ranks swing a lot: the
page prints "of N" beside every rank and dims down × distance cells under 10 plays.

## §12 What to show on caabi.dev
The season dashboard and a target board screenshot; a paragraph on the MLflow lineage (every number on the site
links to the run that produced it) and on the DevSecOps gates (Trivy, SBOM, CodeQL, gitleaks, Sonar) with the
badges.

## §13 CLAUDE.md
See the repository root.
