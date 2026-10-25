"""The numbers behind /v1/games/{game_id}/insights: for both teams the offense's efficiency, tendencies, situations
and the defense's results against the league's season-to-date figures, the quarter lines, the scoring plays, the
biggest win-probability swings and the players behind the offense.

A game is ~170 rows, so the team side is plain Python over the rows the play query already returns (with the FTN
charting columns joined in). The league side is pooled the way the season aggregates are: Σ numerators / Σ denominators
over every play (one aggregate select, `league_play_sums`) or every team-game (`gm.team_game_summary`) through the
last complete week, never a mean of team rates. The play filters are the ones in `ingest/derive/filters.py`."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.engine import Connection

from api.queries import season as season_q
from api.queries.game import _pick, running_scores
from db import schema

P = schema.plays
F = schema.ftn_charting
TGS = schema.team_game_summary
PL = schema.players

BIG_PLAY_EPA = 1.0
IMPACT_PLAYS = 10
IMPACT_PLAYERS = 8

# --------------------------------------------------------------------------- play predicates (one row = one play)


def _flag(r: dict, key: str) -> bool:
    return (r.get(key) or 0) == 1


def clean(r: dict) -> bool:
    return r.get("play_type") in ("pass", "run") and r.get("epa") is not None and not _flag(r, "aborted_play")


def dropback(r: dict) -> bool:
    return _flag(r, "qb_dropback")


def charted(r: dict) -> bool:
    return _flag(r, "charted")


def aligned(r: dict) -> bool:
    return charted(r) and r.get("qb_location") in ("U", "S", "P")


def boxed(r: dict) -> bool:
    return charted(r) and (r.get("n_defense_box") or 0) >= 3


def rushed(r: dict) -> bool:
    return charted(r) and dropback(r) and (r.get("n_pass_rushers") or 0) >= 1


def attempt(r: dict) -> bool:
    return r.get("play_type") == "pass" and not _flag(r, "sack") and r.get("air_yards") is not None


def neutral(r: dict) -> bool:
    wp = r.get("wp")
    return r.get("down") in (1, 2, 3) and wp is not None and 0.1 <= wp <= 0.9 and r.get("xpass") is not None


def designed_run(r: dict) -> bool:
    return r.get("play_type") == "run" and not _flag(r, "qb_scramble")


def _depth(air: float) -> str:
    if air < 0:
        return "behind"
    if air < 10:
        return "short"
    if air < 20:
        return "inter"
    return "deep"


def _box(n: int) -> str:
    return "box_light" if n <= 6 else ("box_7" if n == 7 else "box_8p")


def _rushers(n: int) -> str:
    return "rushers_le3" if n <= 3 else ("rushers_4" if n == 4 else "rushers_5p")


# The sums every rate is built from; `play_sums` (Python, a team's plays) and `league_play_sums` (SQL, the league's
# season) produce the same keys from the same definitions.
SUM_KEYS = (
    "plays dropbacks early early_db d1 d1_db d2 d2_db d3 d3_db shotgun no_huddle charted charted_db play_action "
    "charted_pass screens rpo motion scrambles pressured attempts air_yards deep behind short inter blitzed rushed "
    "rushers rushers_le3 rushers_4 rushers_5p boxed box_light box_7 box_8p aligned align_u align_s align_p pass_loc "
    "pass_left pass_mid pass_right run_loc run_left run_mid run_right fourth fourth_conv late late_epa neutral proe"
).split()


def play_sums(rows: list[dict]) -> dict[str, float]:
    s = dict.fromkeys(SUM_KEYS, 0.0)
    for r in rows:
        if not clean(r):
            continue
        db = dropback(r)
        s["plays"] += 1
        s["dropbacks"] += db
        down = r.get("down")
        if down in (1, 2):
            s["early"] += 1
            s["early_db"] += db
        if down in (1, 2, 3):
            s[f"d{down}"] += 1
            s[f"d{down}_db"] += db
        if down == 4:
            s["fourth"] += 1
            s["fourth_conv"] += _flag(r, "first_down")
        if down in (3, 4):
            s["late"] += 1
            s["late_epa"] += r["epa"]
        s["shotgun"] += _flag(r, "shotgun")
        s["no_huddle"] += _flag(r, "no_huddle")
        if db:
            s["scrambles"] += _flag(r, "qb_scramble")
            s["pressured"] += _flag(r, "sack") or _flag(r, "qb_hit")
        if neutral(r):
            s["neutral"] += 1
            s["proe"] += db - r["xpass"]
        if attempt(r):
            s["attempts"] += 1
            s["air_yards"] += r["air_yards"]
            s[_depth(r["air_yards"])] += 1
        if r.get("play_type") == "pass" and r.get("pass_location") in ("left", "middle", "right"):
            s["pass_loc"] += 1
            s[{"left": "pass_left", "middle": "pass_mid", "right": "pass_right"}[r["pass_location"]]] += 1
        if designed_run(r) and r.get("run_location") in ("left", "middle", "right"):
            s["run_loc"] += 1
            s[{"left": "run_left", "middle": "run_mid", "right": "run_right"}[r["run_location"]]] += 1
        if charted(r):
            s["charted"] += 1
            s["rpo"] += _flag(r, "is_rpo")
            s["motion"] += _flag(r, "is_motion")
            if db:
                s["charted_db"] += 1
                s["play_action"] += _flag(r, "is_play_action")
                s["blitzed"] += (r.get("n_blitzers") or 0) >= 1
            if r.get("play_type") == "pass":
                s["charted_pass"] += 1
                s["screens"] += _flag(r, "is_screen_pass")
            if aligned(r):
                s["aligned"] += 1
                s[{"U": "align_u", "S": "align_s", "P": "align_p"}[r["qb_location"]]] += 1
            if boxed(r):
                s["boxed"] += 1
                s[_box(r["n_defense_box"])] += 1
            if rushed(r):
                s["rushed"] += 1
                s["rushers"] += r["n_pass_rushers"]
                s[_rushers(r["n_pass_rushers"])] += 1
    return s


def league_play_sums(conn: Connection, season: int, through: int | None) -> dict[str, float]:
    """The same sums over every clean play of the season through `through` (all played weeks when None)."""
    db = P.c.qb_dropback == 1
    is_pass, is_run = P.c.play_type == "pass", P.c.play_type == "run"
    has_ftn = F.c.play_id.is_not(None)
    att = and_(is_pass, func.coalesce(P.c.sack, 0) == 0, P.c.air_yards.is_not(None))
    neutral_sql = and_(P.c.down.in_([1, 2, 3]), P.c.wp.between(0.1, 0.9), P.c.xpass.is_not(None))
    aligned_sql = and_(has_ftn, F.c.qb_location.in_(["U", "S", "P"]))
    boxed_sql = and_(has_ftn, F.c.n_defense_box >= 3)
    rushed_sql = and_(has_ftn, db, F.c.n_pass_rushers >= 1)
    left, middle, right = "left", "middle", "right"
    run_loc = and_(is_run, func.coalesce(P.c.qb_scramble, 0) == 0, P.c.run_location.in_([left, middle, right]))
    pass_loc = and_(is_pass, P.c.pass_location.in_([left, middle, right]))

    def n(cond):  # noqa: ANN001, ANN202
        return func.coalesce(func.sum(case((cond, 1), else_=0)), 0)

    def total(cond, col):  # noqa: ANN001, ANN202
        return func.coalesce(func.sum(case((cond, col), else_=0.0)), 0.0)

    exprs = {
        "plays": func.count(),
        "dropbacks": n(db),
        "early": n(P.c.down.in_([1, 2])),
        "early_db": n(and_(P.c.down.in_([1, 2]), db)),
        "d1": n(P.c.down == 1),
        "d1_db": n(and_(P.c.down == 1, db)),
        "d2": n(P.c.down == 2),
        "d2_db": n(and_(P.c.down == 2, db)),
        "d3": n(P.c.down == 3),
        "d3_db": n(and_(P.c.down == 3, db)),
        "shotgun": n(P.c.shotgun == 1),
        "no_huddle": n(P.c.no_huddle == 1),
        "charted": n(has_ftn),
        "charted_db": n(and_(has_ftn, db)),
        "play_action": n(and_(has_ftn, db, F.c.is_play_action == 1)),
        "charted_pass": n(and_(has_ftn, is_pass)),
        "screens": n(and_(has_ftn, is_pass, F.c.is_screen_pass == 1)),
        "rpo": n(and_(has_ftn, F.c.is_rpo == 1)),
        "motion": n(and_(has_ftn, F.c.is_motion == 1)),
        "scrambles": n(and_(db, P.c.qb_scramble == 1)),
        "pressured": n(and_(db, or_(P.c.sack == 1, P.c.qb_hit == 1))),
        "attempts": n(att),
        "air_yards": total(att, P.c.air_yards),
        "deep": n(and_(att, P.c.air_yards >= 20)),
        "behind": n(and_(att, P.c.air_yards < 0)),
        "short": n(and_(att, P.c.air_yards >= 0, P.c.air_yards < 10)),
        "inter": n(and_(att, P.c.air_yards >= 10, P.c.air_yards < 20)),
        "blitzed": n(and_(has_ftn, db, F.c.n_blitzers >= 1)),
        "rushed": n(rushed_sql),
        "rushers": total(rushed_sql, F.c.n_pass_rushers),
        "rushers_le3": n(and_(rushed_sql, F.c.n_pass_rushers <= 3)),
        "rushers_4": n(and_(rushed_sql, F.c.n_pass_rushers == 4)),
        "rushers_5p": n(and_(rushed_sql, F.c.n_pass_rushers >= 5)),
        "boxed": n(boxed_sql),
        "box_light": n(and_(boxed_sql, F.c.n_defense_box <= 6)),
        "box_7": n(and_(boxed_sql, F.c.n_defense_box == 7)),
        "box_8p": n(and_(boxed_sql, F.c.n_defense_box >= 8)),
        "aligned": n(aligned_sql),
        "align_u": n(and_(aligned_sql, F.c.qb_location == "U")),
        "align_s": n(and_(aligned_sql, F.c.qb_location == "S")),
        "align_p": n(and_(aligned_sql, F.c.qb_location == "P")),
        "pass_loc": n(pass_loc),
        "pass_left": n(and_(pass_loc, P.c.pass_location == left)),
        "pass_mid": n(and_(pass_loc, P.c.pass_location == middle)),
        "pass_right": n(and_(pass_loc, P.c.pass_location == right)),
        "run_loc": n(run_loc),
        "run_left": n(and_(run_loc, P.c.run_location == "left")),
        "run_mid": n(and_(run_loc, P.c.run_location == "middle")),
        "run_right": n(and_(run_loc, P.c.run_location == "right")),
        "fourth": n(P.c.down == 4),
        "fourth_conv": n(and_(P.c.down == 4, P.c.first_down == 1)),
        "late": n(P.c.down.in_([3, 4])),
        "late_epa": total(P.c.down.in_([3, 4]), P.c.epa),
        "neutral": n(neutral_sql),
        "proe": total(neutral_sql, P.c.qb_dropback - P.c.xpass),
    }
    stmt = (
        select(*[e.label(k) for k, e in exprs.items()])
        .select_from(P.outerjoin(F, and_(P.c.game_id == F.c.game_id, P.c.play_id == F.c.play_id)))
        .where(
            P.c.season == season,
            P.c.play_type.in_(["pass", "run"]),
            P.c.epa.is_not(None),
            func.coalesce(P.c.aborted_play, 0) == 0,
        )
    )
    if through is not None:
        stmt = stmt.where(P.c.week <= through)
    row = conn.execute(stmt).first()
    return {k: float(v or 0) for k, v in row._mapping.items()} if row else dict.fromkeys(SUM_KEYS, 0.0)


# --------------------------------------------------------------------------- stats


def _rate(num: float, den: float) -> float | None:
    return num / den if den else None


def _mean(values: list) -> float | None:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def stat(  # noqa: PLR0913
    key: str,
    label: str,
    value: float | None,
    n: float,
    league: float | None,
    league_n: float,
    kind: str = "rate",
    better: str = "none",
    rank: int | None = None,
    teams: int | None = None,
) -> dict:
    return {
        "key": key,
        "label": label,
        "value": value,
        "n": int(n or 0),
        "league": league,
        "league_n": int(league_n or 0),
        "rank": rank,
        "teams": teams,
        "kind": kind,
        "better": better,
    }


def _ratio_stat(key: str, label: str, team: dict, league: dict, num: str, den: str, better: str = "none") -> dict:
    return stat(
        key, label, _rate(team[num], team[den]), team[den], _rate(league[num], league[den]), league[den], "rate", better
    )


def _split(key: str, label: str, team: dict, league: dict, den: str, parts: list[tuple[str, str, str]]) -> dict:
    return {
        "key": key,
        "label": label,
        "n": int(team[den]),
        "league_n": int(league[den]),
        "parts": [
            {
                "key": pk,
                "label": pl,
                "count": int(team[col]),
                "share": _rate(team[col], team[den]),
                "league_share": _rate(league[col], league[den]),
            }
            for pk, pl, col in parts
        ],
    }


# gm.team_game_summary metrics: key, label, kind, better, denominator column, ranked by the derive
OFF_EFF = [
    ("epa_per_play", "EPA / play", "epa", "high", "plays", True),
    ("success_rate", "Success rate", "rate", "high", "plays", True),
    ("explosive_rate", "Explosive play rate", "rate", "high", "plays", True),
    ("pass_epa_per_play", "Pass EPA / play", "epa", "high", "pass_plays", True),
    ("rush_epa_per_play", "Rush EPA / play", "epa", "high", "rush_plays", True),
    ("dropback_success", "Dropback success", "rate", "high", "dropbacks", False),
    ("early_down_epa", "Early-down EPA / play", "epa", "high", "early_down_plays", False),
    ("points_per_drive", "Points / drive", "number", "high", "drives", False),
    ("avg_start_yardline", "Avg. start, yds to goal", "number", "low", "drives", False),
]
DEF_EFF = [
    ("epa_per_play", "EPA / play allowed", "epa", "low", "plays", True),
    ("success_rate", "Success rate allowed", "rate", "low", "plays", True),
    ("explosive_rate", "Explosive plays allowed", "rate", "low", "plays", True),
    ("pass_epa_per_play", "Pass EPA / play allowed", "epa", "low", "pass_plays", True),
    ("rush_epa_per_play", "Rush EPA / play allowed", "epa", "low", "rush_plays", True),
    ("third_down_conv", "3rd downs allowed", "rate", "low", "third_downs", False),
    ("red_zone_td_rate", "Red-zone TDs allowed", "rate", "low", "rz_trips", False),
    ("points_per_drive", "Points / drive allowed", "number", "low", "drives", False),
]


def pooled(rows: list[dict], side: str, metric: str, den: str) -> tuple[float | None, int]:
    """Σ(metric × denominator) / Σ denominator over the league's team-game rows: the league's rate by the same definition."""
    pairs = [(r[f"{side}_{metric}"], r[f"{side}_{den}"]) for r in rows]
    pairs = [(v, n) for v, n in pairs if v is not None and n]
    n = sum(p[1] for p in pairs)
    return (sum(v * w for v, w in pairs) / n if n else None, n)


def _summary_stat(
    key: str,
    label: str,
    kind: str,
    better: str,
    metric: str,
    den: str,
    ranked: bool,
    side: str,
    row: dict | None,
    league: list[dict],
) -> dict:
    lg, lg_n = pooled(league, side, metric, den)
    return stat(
        key,
        label,
        row.get(f"{side}_{metric}") if row else None,
        (row.get(f"{side}_{den}") or 0) if row else 0,
        lg,
        lg_n,
        kind,
        better,
        (row.get(f"{side}_{metric}_rank") if ranked and row else None),
        (row.get("week_teams") if ranked and row else None),
    )


def _count_stat(
    key: str, label: str, better: str, metric: str, den: str, side: str, row: dict | None, league: list[dict]
) -> dict:
    """A per-game count (turnovers); the league figure is the average per team-game."""
    vals = [r[f"{side}_{metric}"] for r in league if r[f"{side}_{metric}"] is not None]
    return stat(
        key,
        label,
        row.get(f"{side}_{metric}") if row else None,
        (row.get(f"{side}_{den}") or 0) if row else 0,
        sum(vals) / len(vals) if vals else None,
        len(vals),
        "count",
        better,
    )


# --------------------------------------------------------------------------- scores, quarters, scoring, swings


def _before(run: list[tuple[int, int]], i: int, team: str, g: dict) -> int:
    """The score before play i: the running score after the previous play (`game.running_scores`), 0 at kickoff."""
    return _pick(run[i - 1], team, g) if i > 0 else 0


def _after(run: list[tuple[int, int]], i: int, team: str, g: dict) -> int | None:
    """The score after play i; the final score after the last one, so every point lands on the game."""
    if i + 1 < len(run):
        return _pick(run[i], team, g)
    return g["home_score"] if team == g["home_team"] else g["away_score"]


def quarters(rows: list[dict], team: str, g: dict) -> list[dict]:
    by_q: dict[int, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        if r.get("qtr") is not None:
            by_q[r["qtr"]].append(i)
    run = running_scores(rows)
    out = []
    for q in sorted(by_q):
        idx = by_q[q]
        before, after = _before(run, idx[0], team, g), _after(run, idx[-1], team, g)
        mine = [rows[i] for i in idx if rows[i].get("posteam") == team and clean(rows[i])]
        out.append(
            {
                "qtr": q,
                "label": f"Q{q}" if q <= 4 else "OT",
                "points": after - before if None not in (after, before) else None,
                "plays": len(mine),
                "epa_per_play": _mean([r["epa"] for r in mine]),
                "success_rate": _mean([r.get("success") for r in mine]),
            }
        )
    return out


def scoring(rows: list[dict], g: dict) -> list[dict]:
    """Every play after which a team's score rose; a try (extra point, two-point conversion) folds into the touchdown
    row before it, so a touchdown reads +7 / +6 / +8."""
    out: list[dict] = []
    run = running_scores(rows)
    for i, r in enumerate(rows):
        for team in (g["home_team"], g["away_team"]):
            before, after = _before(run, i, team, g), _after(run, i, team, g)
            if after is None or after <= before:
                continue
            is_try = r.get("play_type") == "extra_point" or "TWO-POINT" in (r.get("desc") or "").upper()
            if is_try and out and out[-1]["team"] == team:
                out[-1]["points"] += after - before
                out[-1]["home_score"], out[-1]["away_score"] = (
                    _after(run, i, g["home_team"], g),
                    _after(run, i, g["away_team"], g),
                )
                continue
            out.append(
                {
                    "play_id": r["play_id"],
                    "qtr": r.get("qtr"),
                    "game_seconds_remaining": r.get("game_seconds_remaining"),
                    "team": team,
                    "desc": r.get("desc"),
                    "points": after - before,
                    "home_score": _after(run, i, g["home_team"], g),
                    "away_score": _after(run, i, g["away_team"], g),
                }
            )
    return out


def impact_plays(rows: list[dict], g: dict) -> list[dict]:
    """The biggest win-probability swings, from the home side so the sign reads one way all game."""
    swings = [r for r in rows if r.get("wpa") is not None and r.get("wp") is not None]
    swings.sort(key=lambda r: abs(r["wpa"]), reverse=True)
    out = []
    for r in swings[:IMPACT_PLAYS]:
        home = r.get("posteam") == g["home_team"]
        before = r["wp"] if home else 1 - r["wp"]
        after = before + (r["wpa"] if home else -r["wpa"])
        out.append(
            {
                "play_id": r["play_id"],
                "drive": r.get("fixed_drive"),
                "qtr": r.get("qtr"),
                "game_seconds_remaining": r.get("game_seconds_remaining"),
                "posteam": r.get("posteam"),
                "defteam": r.get("defteam"),
                "down": r.get("down"),
                "ydstogo": r.get("ydstogo"),
                "yardline_100": r.get("yardline_100"),
                "goal_to_go": r.get("goal_to_go"),
                "play_type": r.get("play_type"),
                "desc": r.get("desc"),
                "yards_gained": r.get("yards_gained"),
                "epa": r.get("epa"),
                "wpa": r["wpa"],
                "home_wp_before": before,
                "home_wp_after": min(1.0, max(0.0, after)),
                "touchdown": r.get("touchdown"),
                "interception": r.get("interception"),
                "fumble_lost": r.get("fumble_lost"),
                "sack": r.get("sack"),
                "penalty": r.get("penalty"),
                "fourth_down": r.get("down") == 4,
                "posteam_score": r.get("posteam_score"),
                "defteam_score": r.get("defteam_score"),
            }
        )
    return out


def players(rows: list[dict], team: str, names: dict[str, tuple[str | None, str | None]]) -> list[dict]:
    """Credit each clean play to the passer (passes), the rusher (runs, a scramble's QB included) and the target."""
    acc: dict[str, dict] = {}
    for r in rows:
        if r.get("posteam") != team or not clean(r):
            continue
        credits = []
        if r["play_type"] == "pass" and r.get("passer_player_id"):
            credits.append((r["passer_player_id"], "as_passer"))
        if r["play_type"] == "run" and r.get("rusher_player_id"):
            credits.append((r["rusher_player_id"], "as_rusher"))
        if r.get("receiver_player_id"):
            credits.append((r["receiver_player_id"], "as_receiver"))
        for pid, role in credits:
            p = acc.setdefault(
                pid,
                {
                    "gsis_id": pid,
                    "name": names.get(pid, (None, None))[0],
                    "position": names.get(pid, (None, None))[1],
                    "team": team,
                    "plays": 0,
                    "as_passer": 0,
                    "as_rusher": 0,
                    "as_receiver": 0,
                    "yards": 0,
                    "epa": 0.0,
                    "wpa": 0.0,
                    "big_plays": 0,
                },
            )
            p["plays"] += 1
            p[role] += 1
            p["yards"] += r.get("yards_gained") or 0
            p["epa"] += r["epa"]
            p["wpa"] += r.get("wpa") or 0.0
            p["big_plays"] += abs(r["epa"]) >= BIG_PLAY_EPA
    out = sorted(acc.values(), key=lambda p: abs(p["wpa"]), reverse=True)
    return out[:IMPACT_PLAYERS]


def player_names(conn: Connection, rows: list[dict]) -> dict[str, tuple[str | None, str | None]]:
    ids = {r[k] for r in rows for k in ("passer_player_id", "rusher_player_id", "receiver_player_id") if r.get(k)}
    if not ids:
        return {}
    stmt = select(PL.c.gsis_id, PL.c.display_name, PL.c.position).where(PL.c.gsis_id.in_(sorted(ids)))
    return {r.gsis_id: (r.display_name, r.position) for r in conn.execute(stmt)}


# --------------------------------------------------------------------------- one team


def team_insights(  # noqa: PLR0913
    team: str,
    opp: str,
    g: dict,
    rows: list[dict],
    summary: dict | None,
    league_rows: list[dict],
    league: dict[str, float],
    names: dict[str, tuple[str | None, str | None]],
) -> dict:
    mine = play_sums([r for r in rows if r.get("posteam") == team])
    theirs = play_sums([r for r in rows if r.get("posteam") == opp])  # what this team's defense faced
    efficiency = [
        _summary_stat(k, lb, kd, bt, k, den, rk, "off", summary, league_rows) for k, lb, kd, bt, den, rk in OFF_EFF
    ]
    tendencies = [
        _ratio_stat("pass_rate", "Dropback rate", mine, league, "dropbacks", "plays"),
        stat(
            "proe",
            "Pass rate over expected",
            _rate(mine["proe"], mine["neutral"]),
            mine["neutral"],
            _rate(league["proe"], league["neutral"]),
            league["neutral"],
            "rate",
            "none",
            summary.get("off_proe_rank") if summary else None,
            summary.get("week_teams") if summary else None,
        ),
        _ratio_stat("early_down_pass_rate", "Early-down dropback rate", mine, league, "early_db", "early"),
        _ratio_stat("shotgun_rate", "Shotgun snaps (incl. pistol)", mine, league, "shotgun", "plays"),
        _ratio_stat("no_huddle_rate", "No huddle", mine, league, "no_huddle", "plays"),
        _ratio_stat("play_action_rate", "Play action", mine, league, "play_action", "charted_db"),
        _ratio_stat("screen_rate", "Screens", mine, league, "screens", "charted_pass"),
        _ratio_stat("rpo_rate", "RPO", mine, league, "rpo", "charted"),
        _ratio_stat("motion_rate", "Pre-snap motion", mine, league, "motion", "charted"),
        _ratio_stat("scramble_rate", "Scrambles", mine, league, "scrambles", "dropbacks"),
        _ratio_stat("pressure_rate_taken", "Pressured (sack or QB hit)", mine, league, "pressured", "dropbacks", "low"),
        stat(
            "adot",
            "Avg. depth of target",
            _rate(mine["air_yards"], mine["attempts"]),
            mine["attempts"],
            _rate(league["air_yards"], league["attempts"]),
            league["attempts"],
            "number",
        ),
        _ratio_stat("deep_rate", "Deep targets (20+ air yds)", mine, league, "deep", "attempts"),
        _ratio_stat("blitz_rate_faced", "Blitzed", mine, league, "blitzed", "charted_db"),
        stat(
            "pass_rushers_faced",
            "Pass rushers faced",
            _rate(mine["rushers"], mine["rushed"]),
            mine["rushed"],
            _rate(league["rushers"], league["rushed"]),
            league["rushed"],
            "number",
        ),
        _ratio_stat("light_box_rate_faced", "Light boxes faced (6 or fewer)", mine, league, "box_light", "boxed"),
    ]
    by_down = [
        _ratio_stat("pass_rate_1st", "1st down", mine, league, "d1_db", "d1"),
        _ratio_stat("pass_rate_2nd", "2nd down", mine, league, "d2_db", "d2"),
        _ratio_stat("pass_rate_3rd", "3rd down", mine, league, "d3_db", "d3"),
    ]
    run = {**mine, "run": mine["plays"] - mine["dropbacks"]}
    run_lg = {**league, "run": league["plays"] - league["dropbacks"]}
    splits = [
        _split(
            "qb_alignment",
            "QB alignment",
            mine,
            league,
            "aligned",
            [
                ("under_center", "Under center", "align_u"),
                ("shotgun", "Shotgun", "align_s"),
                ("pistol", "Pistol", "align_p"),
            ],
        ),
        _split(
            "run_pass",
            "Dropback vs run",
            run,
            run_lg,
            "plays",
            [("dropback", "Dropback", "dropbacks"), ("run", "Designed run", "run")],
        ),
        _split(
            "pass_location",
            "Pass direction",
            mine,
            league,
            "pass_loc",
            [("left", "Left", "pass_left"), ("middle", "Middle", "pass_mid"), ("right", "Right", "pass_right")],
        ),
        _split(
            "run_location",
            "Run direction",
            mine,
            league,
            "run_loc",
            [("left", "Left", "run_left"), ("middle", "Middle", "run_mid"), ("right", "Right", "run_right")],
        ),
        _split(
            "target_depth",
            "Target depth",
            mine,
            league,
            "attempts",
            [
                ("behind", "Behind the line", "behind"),
                ("short", "Short, 0–9", "short"),
                ("intermediate", "Intermediate, 10–19", "inter"),
                ("deep", "Deep, 20+", "deep"),
            ],
        ),
        _split(
            "box_faced",
            "Defenders in the box faced",
            mine,
            league,
            "boxed",
            [("light", "6 or fewer", "box_light"), ("seven", "7", "box_7"), ("stacked", "8 or more", "box_8p")],
        ),
    ]
    situations = [
        _summary_stat(
            "third_down_conv",
            "3rd-down conversions",
            "rate",
            "high",
            "third_down_conv",
            "third_downs",
            False,
            "off",
            summary,
            league_rows,
        ),
        _ratio_stat("fourth_down_conv", "4th-down conversions", mine, league, "fourth_conv", "fourth", "high"),
        _summary_stat(
            "red_zone_td_rate",
            "Red-zone touchdowns",
            "rate",
            "high",
            "red_zone_td_rate",
            "rz_trips",
            False,
            "off",
            summary,
            league_rows,
        ),
        stat(
            "late_down_epa",
            "3rd & 4th-down EPA / play",
            _rate(mine["late_epa"], mine["late"]),
            mine["late"],
            _rate(league["late_epa"], league["late"]),
            league["late"],
            "epa",
            "high",
        ),
        _summary_stat(
            "sack_rate", "Sacked", "rate", "low", "sack_rate", "dropbacks", False, "off", summary, league_rows
        ),
        _count_stat(
            "turnovers", "Turnovers (incl. on downs)", "low", "turnovers", "drives", "off", summary, league_rows
        ),
    ]
    defense = [
        _summary_stat(f"def_{k}", lb, kd, bt, k, den, rk, "def", summary, league_rows)
        for k, lb, kd, bt, den, rk in DEF_EFF
    ]
    defense += [
        _count_stat(
            "takeaways", "Takeaways (incl. on downs)", "high", "turnovers", "drives", "def", summary, league_rows
        ),
        _summary_stat(
            "sack_rate_made",
            "Sacks per dropback",
            "rate",
            "high",
            "sack_rate",
            "dropbacks",
            False,
            "def",
            summary,
            league_rows,
        ),
        _ratio_stat("pressure_rate", "Pressure rate (sack or hit)", theirs, league, "pressured", "dropbacks", "high"),
        _ratio_stat("blitz_rate", "Blitz rate", theirs, league, "blitzed", "charted_db"),
        stat(
            "pass_rushers",
            "Pass rushers sent",
            _rate(theirs["rushers"], theirs["rushed"]),
            theirs["rushed"],
            _rate(league["rushers"], league["rushed"]),
            league["rushed"],
            "number",
        ),
        _ratio_stat("light_box_rate", "Light boxes shown (6 or fewer)", theirs, league, "box_light", "boxed"),
    ]
    defense_splits = [
        _split(
            "box_shown",
            "Defenders in the box",
            theirs,
            league,
            "boxed",
            [("light", "6 or fewer", "box_light"), ("seven", "7", "box_7"), ("stacked", "8 or more", "box_8p")],
        ),
        _split(
            "pass_rushers_sent",
            "Pass rushers",
            theirs,
            league,
            "rushed",
            [
                ("three_or_fewer", "3 or fewer", "rushers_le3"),
                ("four", "4", "rushers_4"),
                ("five_plus", "5 or more", "rushers_5p"),
            ],
        ),
    ]
    home = team == g["home_team"]
    return {
        "team": team,
        "opponent": opp,
        "is_home": home,
        "points": g["home_score"] if home else g["away_score"],
        "quarters": quarters(rows, team, g) if rows else [],
        "efficiency": efficiency,
        "tendencies": tendencies,
        "by_down": by_down,
        "splits": splits,
        "situations": situations,
        "defense": defense,
        "defense_splits": defense_splits,
        "players": players(rows, team, names),
    }


# --------------------------------------------------------------------------- the response


def build(conn: Connection, g: dict, focus: str, rows: list[dict]) -> dict:
    opp = g["away_team"] if focus == g["home_team"] else g["home_team"]
    games = season_q.games(conn, g["season"])
    through = season_q.through_week(games)
    league_rows = [r for r in season_q.team_weeks(conn, g["season"]) if through is None or r["week"] <= through]
    league = league_play_sums(conn, g["season"], through)
    summaries = {
        r["team"]: r
        for r in conn.execute(select(TGS).where(and_(TGS.c.game_id == g["game_id"], TGS.c.team.in_([focus, opp]))))
        .mappings()
        .all()
    }
    names = player_names(conn, rows)
    return {
        **{k: g[k] for k in ("game_id", "season", "week", "home_team", "away_team", "home_score", "away_score")},
        "played": g["result"] is not None,
        "team": focus,
        "opponent": opp,
        "league_through_week": through,
        "league_teams": len({r["team"] for r in league_rows}),
        "charted": any(charted(r) for r in rows),
        "teams": [
            team_insights(focus, opp, g, rows, summaries.get(focus), league_rows, league, names),
            team_insights(opp, focus, g, rows, summaries.get(opp), league_rows, league, names),
        ],
        "impact_plays": impact_plays(rows, g),
        "scoring": scoring(rows, g),
    }
