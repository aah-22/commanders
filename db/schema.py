"""SQLAlchemy 2.0 schema shared by the API and the jobs.

Postgres schemas: `nfl` (raw nflverse mirrors, natural keys, upserted), `gm` (derived), `ml` (model outputs),
`ops` (pipeline bookkeeping). On SQLite (tests) the schemas are translated away with `sqlite_options()`.
The nflverse spread / total / moneyline columns are deliberately not mirrored anywhere.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Index, Integer, MetaData, String, Table, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMAS = ("nfl", "gm", "ml", "ops")


def sqlite_options() -> dict:
    """Execution options that collapse the Postgres schemas into plain tables on SQLite."""
    return {"schema_translate_map": dict.fromkeys(SCHEMAS)}


class Base(DeclarativeBase):
    pass


metadata: MetaData = Base.metadata


class PipelineRun(Base):
    """One row per job invocation (ingest / derive / train / score), mirroring the MLflow run."""

    __tablename__ = "pipeline_runs"
    __table_args__ = {"schema": "ops"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)
    run_id: Mapped[str | None] = mapped_column(String(64))
    season: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="running")
    rows: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DatasetVersion(Base):
    """Digest of each nflverse asset as last ingested, so an unchanged file is skipped (and still logged)."""

    __tablename__ = "dataset_versions"
    __table_args__ = {"schema": "ops"}

    dataset: Mapped[str] = mapped_column(String(40), primary_key=True)
    season: Mapped[int] = mapped_column(Integer, primary_key=True)  # 0 for season-less assets
    source_url: Mapped[str | None] = mapped_column(Text)
    digest: Mapped[str | None] = mapped_column(String(64))
    rows: Mapped[int | None] = mapped_column(Integer)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Game(Base):
    """nflverse schedules, one row per game."""

    __tablename__ = "games"
    __table_args__ = {"schema": "nfl"}

    game_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    week: Mapped[int] = mapped_column(Integer, index=True)
    game_type: Mapped[str] = mapped_column(String(8))
    gameday: Mapped[str | None] = mapped_column(String(10))
    weekday: Mapped[str | None] = mapped_column(String(10))
    gametime: Mapped[str | None] = mapped_column(String(8))
    home_team: Mapped[str] = mapped_column(String(4), index=True)
    away_team: Mapped[str] = mapped_column(String(4), index=True)
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    result: Mapped[int | None] = mapped_column(Integer)  # home margin; NULL until played
    total: Mapped[int | None] = mapped_column(Integer)
    overtime: Mapped[int | None] = mapped_column(Integer)
    div_game: Mapped[int | None] = mapped_column(Integer)
    location: Mapped[str | None] = mapped_column(String(8))
    roof: Mapped[str | None] = mapped_column(String(16))
    surface: Mapped[str | None] = mapped_column(String(16))
    temp: Mapped[int | None] = mapped_column(Integer)
    wind: Mapped[int | None] = mapped_column(Integer)
    away_qb_id: Mapped[str | None] = mapped_column(String(16))
    home_qb_id: Mapped[str | None] = mapped_column(String(16))
    away_qb_name: Mapped[str | None] = mapped_column(String(64))
    home_qb_name: Mapped[str | None] = mapped_column(String(64))
    away_coach: Mapped[str | None] = mapped_column(String(64))
    home_coach: Mapped[str | None] = mapped_column(String(64))
    away_rest: Mapped[int | None] = mapped_column(Integer)
    home_rest: Mapped[int | None] = mapped_column(Integer)
    stadium: Mapped[str | None] = mapped_column(Text)


# --------------------------------------------------------------------------- raw mirrors (Core tables)
def _cols(spec: str, types: dict[str, type] | None = None) -> list[Column]:
    """'a b c' → Float columns except those named in `types` (a compact way to declare wide stat tables)."""
    types = types or {}
    return [Column(name, types.get(name, Float)) for name in spec.split()]


teams = Table(
    "teams",
    metadata,
    Column("team_abbr", String(4), primary_key=True),
    Column("team_name", String(48)),
    Column("team_id", String(8)),
    Column("team_nick", String(24)),
    Column("team_conf", String(4)),
    Column("team_division", String(16)),
    Column("team_color", String(8)),
    Column("team_color2", String(8)),
    Column("team_logo_wikipedia", Text),
    Column("team_logo_espn", Text),
    Column("team_wordmark", Text),
    schema="nfl",
)

players = Table(
    "players",
    metadata,
    Column("gsis_id", String(16), primary_key=True),
    Column("display_name", String(64)),
    Column("first_name", String(48)),
    Column("last_name", String(48)),
    Column("football_name", String(48)),
    Column("esb_id", String(16)),
    Column("pfr_id", String(16)),
    Column("pff_id", String(16)),
    Column("otc_id", String(16)),
    Column("espn_id", String(16)),
    Column("birth_date", String(10)),
    Column("position_group", String(8)),
    Column("position", String(8)),
    Column("height", Float),
    Column("weight", Float),
    Column("college_name", String(64)),
    Column("jersey_number", Float),
    Column("rookie_season", Float),
    Column("last_season", Float),
    Column("latest_team", String(4)),
    Column("status", String(8)),
    Column("years_of_experience", Float),
    Column("draft_year", Float),
    Column("draft_round", Float),
    Column("draft_pick", Float),
    Column("draft_team", String(4)),
    Column("headshot", Text),
    Index("ix_players_pfr", "pfr_id"),
    Index("ix_players_otc", "otc_id"),
    Index("ix_players_pos_team", "position", "latest_team"),
    schema="nfl",
)

plays = Table(
    "plays",
    metadata,
    Column("game_id", String(24), primary_key=True),
    Column("play_id", Integer, primary_key=True),
    Column("season", Integer, nullable=False),
    Column("week", Integer),
    Column("posteam", String(4)),
    Column("defteam", String(4)),
    Column("home_team", String(4)),
    Column("away_team", String(4)),
    Column("fixed_drive", Integer),
    Column("drive", Integer),
    Column("qtr", Integer),
    Column("down", Integer),
    Column("ydstogo", Integer),
    Column("yardline_100", Integer),
    Column("goal_to_go", Integer),
    Column("game_seconds_remaining", Integer),
    Column("half_seconds_remaining", Integer),
    Column("play_type", String(24)),
    Column("desc", Text),
    Column("yards_gained", Integer),
    *_cols("epa qb_epa success wp wpa air_yards yards_after_catch cpoe xpass"),
    *_cols(
        "pass rush qb_dropback qb_scramble qb_kneel qb_spike shotgun no_huddle sack qb_hit interception "
        "fumble_lost touchdown penalty complete_pass incomplete_pass first_down series_success aborted_play",
        dict.fromkeys(
            "pass rush qb_dropback qb_scramble qb_kneel qb_spike shotgun no_huddle sack qb_hit interception "
            "fumble_lost touchdown penalty complete_pass incomplete_pass first_down series_success aborted_play".split(),
            Integer,
        ),
    ),
    Column("passer_player_id", String(16)),
    Column("rusher_player_id", String(16)),
    Column("receiver_player_id", String(16)),
    Column("penalty_player_id", String(16)),
    Column("pass_location", String(8)),
    Column("run_location", String(8)),
    Column("series", Integer),
    Column("fixed_drive_result", String(24)),
    Column("td_team", String(4)),
    Column("posteam_score", Integer),
    Column("defteam_score", Integer),
    Column("score_differential", Integer),
    Column("total_home_score", Integer),
    Column("total_away_score", Integer),
    Index("ix_plays_season_pos", "season", "posteam"),
    Index("ix_plays_season_def", "season", "defteam"),
    Index("ix_plays_drive", "game_id", "fixed_drive"),
    Index("ix_plays_passer", "passer_player_id"),
    Index("ix_plays_rusher", "rusher_player_id"),
    Index("ix_plays_receiver", "receiver_player_id"),
    schema="nfl",
)

_pgs_ints = "season week completions attempts passing_yards passing_tds passing_interceptions sacks_suffered carries rushing_yards rushing_tds receptions targets receiving_yards receiving_tds"
player_game_stats = Table(
    "player_game_stats",
    metadata,
    Column("player_id", String(16), primary_key=True),
    Column("game_id", String(24), primary_key=True),
    Column("player_display_name", String(64)),
    Column("position", String(8)),
    Column("position_group", String(8)),
    Column("season_type", String(8)),
    Column("team", String(4)),
    Column("opponent_team", String(4)),
    *_cols(
        "season week completions attempts passing_yards passing_tds passing_interceptions sacks_suffered sack_yards_lost "
        "passing_air_yards passing_yards_after_catch passing_first_downs passing_epa passing_cpoe pacr carries rushing_yards "
        "rushing_tds rushing_fumbles_lost rushing_first_downs rushing_epa receptions targets receiving_yards receiving_tds "
        "receiving_fumbles_lost receiving_air_yards receiving_yards_after_catch receiving_first_downs receiving_epa racr "
        "target_share air_yards_share wopr def_tackles_solo def_tackles_with_assist def_tackle_assists def_tackles_for_loss "
        "def_fumbles_forced def_sacks def_qb_hits def_interceptions def_pass_defended def_tds",
        dict.fromkeys(_pgs_ints.split(), Integer),
    ),
    Index("ix_pgs_season_week", "season", "week"),
    Index("ix_pgs_team_season", "team", "season"),
    schema="nfl",
)

_tgs_ints = (
    "season week completions attempts passing_yards passing_tds passing_interceptions sacks_suffered carries rushing_yards "
    "rushing_tds receptions targets receiving_yards receiving_tds penalties fg_made fg_att pat_made pat_att pt_att"
)
team_game_stats = Table(
    "team_game_stats",
    metadata,
    Column("team", String(4), primary_key=True),
    Column("game_id", String(24), primary_key=True),
    Column("season_type", String(8)),
    Column("opponent_team", String(4)),
    *_cols(
        "season week completions attempts passing_yards passing_tds passing_interceptions sacks_suffered sack_yards_lost "
        "sack_fumbles_lost passing_air_yards passing_yards_after_catch passing_first_downs passing_epa passing_cpoe carries "
        "rushing_yards rushing_tds rushing_fumbles_lost rushing_first_downs rushing_epa receptions targets receiving_yards "
        "receiving_tds receiving_fumbles_lost receiving_first_downs receiving_epa special_teams_tds def_tackles_for_loss "
        "def_fumbles_forced def_sacks def_qb_hits def_interceptions def_pass_defended def_tds def_safeties penalties "
        "penalty_yards fumbles_lost_total fg_made fg_att pat_made pat_att pt_att pt_net_yards",
        dict.fromkeys(_tgs_ints.split(), Integer),
    ),
    Index("ix_tgs_season_week", "season", "week"),
    schema="nfl",
)

snap_counts = Table(
    "snap_counts",
    metadata,
    Column("pfr_player_id", String(16), primary_key=True),
    Column("game_id", String(24), primary_key=True),
    Column("gsis_id", String(16)),
    Column("season", Integer),
    Column("week", Integer),
    Column("game_type", String(8)),
    Column("player", String(64)),
    Column("position", String(8)),
    Column("team", String(4)),
    Column("opponent", String(4)),
    *_cols("offense_snaps offense_pct defense_snaps defense_pct st_snaps st_pct"),
    Index("ix_snaps_gsis", "gsis_id"),
    Index("ix_snaps_season_team", "season", "team"),
    schema="nfl",
)

rosters_weekly = Table(
    "rosters_weekly",
    metadata,
    Column("season", Integer, primary_key=True),
    Column("week", Integer, primary_key=True),
    Column("team", String(4), primary_key=True),
    Column("gsis_id", String(16), primary_key=True),
    Column("game_type", String(8)),
    Column("position", String(8)),
    Column("depth_chart_position", String(8)),
    Column("jersey_number", Float),
    Column("status", String(8)),
    Column("full_name", String(64)),
    Column("birth_date", String(10)),
    Column("height", Float),
    Column("weight", Float),
    Column("college", String(64)),
    Column("pfr_id", String(16)),
    Column("espn_id", String(16)),
    Column("years_exp", Float),
    Column("entry_year", Float),
    Column("rookie_year", Float),
    Column("draft_club", String(4)),
    Column("draft_number", Float),
    Index("ix_rw_gsis", "gsis_id"),
    schema="nfl",
)

depth_charts = Table(
    "depth_charts",
    metadata,
    Column("season", Integer, primary_key=True),
    Column("week", Integer, primary_key=True),
    Column("team", String(4), primary_key=True),
    Column("gsis_id", String(16), primary_key=True),
    Column("pos_abb", String(8), primary_key=True),
    Column("dt", String(32)),
    Column("player_name", String(64)),
    Column("espn_id", String(16)),
    Column("pos_grp", String(16)),
    Column("pos_name", String(32)),
    Column("pos_slot", Integer),
    Column("pos_rank", Integer),
    schema="nfl",
)

injuries = Table(
    "injuries",
    metadata,
    Column("season", Integer, primary_key=True),
    Column("week", Integer, primary_key=True),
    Column("game_type", String(8), primary_key=True),
    Column("gsis_id", String(16), primary_key=True),
    Column("season_type", String(8)),
    Column("team", String(4)),
    Column("position", String(8)),
    Column("full_name", String(64)),
    Column("report_primary_injury", String(48)),
    Column("report_secondary_injury", String(48)),
    Column("report_status", String(24)),
    Column("practice_primary_injury", String(48)),
    Column("practice_secondary_injury", String(48)),
    Column("practice_status", String(48)),
    schema="nfl",
)

contracts = Table(
    "contracts",
    metadata,
    Column("otc_id", String(16), primary_key=True),
    Column("year_signed", Integer, primary_key=True),
    Column("team_raw", String(32), primary_key=True),
    Column("team_abbr", String(4)),
    Column("player", String(64)),
    Column("position", String(8)),
    Column("gsis_id", String(16)),
    Column("is_active", Boolean),
    *_cols("years value apy guaranteed apy_cap_pct inflated_value inflated_apy inflated_guaranteed"),
    Column("draft_year", Float),
    Column("draft_round", Float),
    Column("draft_overall", Float),
    Column("draft_team", String(4)),
    Column("date_of_birth", String(10)),
    Column("college", String(64)),
    Column("player_page", Text),
    Index("ix_contracts_gsis", "gsis_id"),
    Index("ix_contracts_active_pos", "is_active", "position"),
    schema="nfl",
)

contract_seasons = Table(
    "contract_seasons",
    metadata,
    Column("otc_id", String(16), primary_key=True),
    Column("year_signed", Integer, primary_key=True),
    Column("team_raw", String(32), primary_key=True),
    Column("season", Integer, primary_key=True),
    Column("team", String(24)),
    *_cols(
        "base_salary prorated_bonus option_bonus roster_bonus guaranteed_salary cap_number cap_percent cash_paid workout_bonus per_game_roster_bonus other_bonus"
    ),
    schema="nfl",
)

draft_picks = Table(
    "draft_picks",
    metadata,
    Column("season", Integer, primary_key=True),
    Column("round", Integer, primary_key=True),
    Column("pick", Integer, primary_key=True),
    Column("team", String(4)),
    Column("gsis_id", String(16)),
    Column("pfr_player_id", String(16)),
    Column("pfr_player_name", String(64)),
    Column("position", String(8)),
    Column("category", String(8)),
    Column("side", String(8)),
    Column("college", String(64)),
    Column("age", Float),
    Column("to", Float),
    *_cols("allpro probowls seasons_started w_av car_av dr_av games"),
    Index("ix_draft_gsis", "gsis_id"),
    Index("ix_draft_team", "team"),
    schema="nfl",
)

trades = Table(
    "trades",
    metadata,
    Column("trade_id", Integer, primary_key=True),
    Column("seq", Integer, primary_key=True),
    Column("season", Integer),
    Column("trade_date", String(10)),
    Column("gave", String(4)),
    Column("received", String(4)),
    Column("pick_season", Float),
    Column("pick_round", Float),
    Column("pick_number", Float),
    Column("conditional", Float),
    Column("pfr_id", String(16)),
    Column("pfr_name", String(64)),
    Column("gsis_id", String(16)),
    Index("ix_trades_received", "received", "season"),
    Index("ix_trades_gsis", "gsis_id"),
    schema="nfl",
)


def _pfr(name: str, stats: str) -> Table:
    return Table(
        name,
        metadata,
        Column("pfr_player_id", String(16), primary_key=True),
        Column("game_id", String(24), primary_key=True),
        Column("gsis_id", String(16)),
        Column("season", Integer),
        Column("week", Integer),
        Column("game_type", String(8)),
        Column("team", String(4)),
        Column("opponent", String(4)),
        Column("pfr_player_name", String(64)),
        *_cols(stats),
        Index(f"ix_{name}_gsis", "gsis_id"),
        Index(f"ix_{name}_season_team", "season", "team"),
        schema="nfl",
    )


pfr_def_game = _pfr(
    "pfr_def_game",
    "def_ints def_targets def_completions_allowed def_completion_pct def_yards_allowed "
    "def_yards_allowed_per_cmp def_yards_allowed_per_tgt def_receiving_td_allowed def_passer_rating_allowed "
    "def_adot def_air_yards_completed def_yards_after_catch def_times_blitzed def_times_hurried def_times_hitqb "
    "def_sacks def_pressures def_tackles_combined def_missed_tackles def_missed_tackle_pct",
)
pfr_pass_game = _pfr(
    "pfr_pass_game",
    "passing_drops passing_drop_pct passing_bad_throws passing_bad_throw_pct times_sacked "
    "times_blitzed times_hurried times_hit times_pressured times_pressured_pct",
)
pfr_rush_game = _pfr(
    "pfr_rush_game",
    "carries rushing_yards_before_contact rushing_yards_before_contact_avg "
    "rushing_yards_after_contact rushing_yards_after_contact_avg rushing_broken_tackles receiving_broken_tackles",
)
pfr_rec_game = _pfr(
    "pfr_rec_game", "receiving_broken_tackles receiving_drop receiving_drop_pct receiving_int receiving_rat"
)


def _ngs(name: str, stats: str) -> Table:
    return Table(
        name,
        metadata,
        Column("season", Integer, primary_key=True),
        Column("season_type", String(8), primary_key=True),
        Column("week", Integer, primary_key=True),
        Column("player_gsis_id", String(16), primary_key=True),
        Column("player_display_name", String(64)),
        Column("player_position", String(8)),
        Column("team_abbr", String(4)),
        *_cols(stats),
        schema="nfl",
    )


ngs_passing = _ngs(
    "ngs_passing",
    "avg_time_to_throw avg_completed_air_yards avg_intended_air_yards avg_air_yards_differential "
    "aggressiveness max_completed_air_distance avg_air_yards_to_sticks attempts pass_yards pass_touchdowns "
    "interceptions passer_rating completions completion_percentage expected_completion_percentage "
    "completion_percentage_above_expectation avg_air_distance max_air_distance",
)
ngs_rushing = _ngs(
    "ngs_rushing",
    "efficiency percent_attempts_gte_eight_defenders avg_time_to_los rush_attempts rush_yards "
    "avg_rush_yards rush_touchdowns expected_rush_yards rush_yards_over_expected rush_yards_over_expected_per_att "
    "rush_pct_over_expected",
)
ngs_receiving = _ngs(
    "ngs_receiving",
    "avg_cushion avg_separation avg_intended_air_yards percent_share_of_intended_air_yards "
    "receptions targets catch_percentage yards rec_touchdowns avg_yac avg_expected_yac avg_yac_above_expectation",
)

MIRRORS: dict[str, Table] = {
    t.name: t
    for t in (
        teams,
        players,
        Game.__table__,
        plays,
        player_game_stats,
        team_game_stats,
        snap_counts,
        rosters_weekly,
        depth_charts,
        injuries,
        contracts,
        contract_seasons,
        draft_picks,
        trades,
        pfr_def_game,
        pfr_pass_game,
        pfr_rush_game,
        pfr_rec_game,
        ngs_passing,
        ngs_rushing,
        ngs_receiving,
    )
}


# --------------------------------------------------------------------------- derived (gm.*), rebuilt per season
# One side's metrics; stored with an off_ prefix (team on offense) and a def_ prefix (team on defense, i.e. allowed).
SIDE_RATES = (
    "epa_per_play success_rate explosive_rate pass_epa_per_play rush_epa_per_play dropback_success early_down_epa "
    "pass_rate proe third_down_conv red_zone_td_rate sack_rate points_per_drive avg_start_yardline nflv_pass_epa "
    "nflv_rush_epa"
)
SIDE_COUNTS = (
    "plays pass_plays rush_plays dropbacks early_down_plays neutral_plays third_downs rz_trips sacks drives turnovers "
    "turnovers_on_downs"
)
RANKED = {
    "off": "epa_per_play success_rate explosive_rate proe pass_epa_per_play rush_epa_per_play".split(),
    "def": "epa_per_play success_rate explosive_rate pass_epa_per_play rush_epa_per_play".split(),
}


def side_columns(prefix: str) -> list[str]:
    return [f"{prefix}_{c}" for c in (SIDE_RATES + " " + SIDE_COUNTS).split()] + [
        f"{prefix}_{c}_rank" for c in RANKED[prefix]
    ]


team_game_summary = Table(
    "team_game_summary",
    metadata,
    Column("season", Integer, primary_key=True),
    Column("week", Integer, primary_key=True),
    Column("team", String(4), primary_key=True),
    Column("game_id", String(24), nullable=False),
    Column("opponent", String(4)),
    Column("is_home", Boolean),
    Column("game_type", String(8)),
    Column("points_for", Integer),
    Column("points_against", Integer),
    Column("result", String(1)),
    Column("week_teams", Integer),
    *[
        Column(c, Integer if c.split("_", 1)[1] in SIDE_COUNTS.split() or c.endswith("_rank") else Float)
        for c in side_columns("off") + side_columns("def")
    ],
    Index("ix_tgs_season_team", "season", "team"),
    Index("ix_tgs_game", "game_id"),
    schema="gm",
)

standings = Table(
    "standings",
    metadata,
    Column("season", Integer, primary_key=True),
    Column("week", Integer, primary_key=True),
    Column("team", String(4), primary_key=True),
    Column("conf", String(4)),
    Column("division", String(16)),
    *_cols(
        "wins losses ties games_played pf pa point_diff div_rank conf_rank",
        dict.fromkeys("wins losses ties games_played pf pa point_diff div_rank conf_rank".split(), Integer),
    ),
    *_cols("win_pct pythag_win_pct"),
    schema="gm",
)

DERIVED: dict[str, Table] = {t.name: t for t in (team_game_summary, standings)}
