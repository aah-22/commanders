"""Position groups for the GM lens, the headline production metric of each, and the thresholds behind percentiles,
starters and the need score. Everything the pages say about "position" starts here.

Sources disagree on positions: OTC contracts are precise (ED / IDL / LT / RG …), depth charts are slots (RDE, NB), the
2025+ weekly rosters are coarse (OL / DL / DB) and `nfl.players` is somewhere between. `group_expr` takes the first
non-null source in that order."""

from __future__ import annotations

import polars as pl

GROUPS = ["QB", "RB", "WR", "TE", "OL", "IDL", "ED", "LB", "CB", "S", "ST"]

# any label any source uses → group
_MAP: dict[str, str] = {
    **dict.fromkeys(["QB"], "QB"),
    **dict.fromkeys(["RB", "HB", "FB"], "RB"),
    **dict.fromkeys(["WR"], "WR"),
    **dict.fromkeys(["TE"], "TE"),
    **dict.fromkeys(["OL", "T", "G", "C", "LT", "LG", "RG", "RT", "OT", "OG", "IOL"], "OL"),
    **dict.fromkeys(["IDL", "DT", "NT", "DL"], "IDL"),
    **dict.fromkeys(["ED", "EDGE", "DE", "OLB", "LDE", "RDE", "LOLB", "ROLB"], "ED"),
    **dict.fromkeys(["LB", "ILB", "MLB", "LILB", "RILB", "MIKE", "WILL", "SAM"], "LB"),
    **dict.fromkeys(["CB", "NB", "NCB", "LCB", "RCB", "SLOT_CB", "DB"], "CB"),
    **dict.fromkeys(["S", "FS", "SS", "SAF", "SAFETY"], "S"),
    **dict.fromkeys(["K", "P", "LS", "PK", "KO", "SPEC"], "ST"),
}

# headline metric per group; `higher` False means a low value is good (percentiles are flipped)
HEADLINE: dict[str, tuple[str, bool]] = {
    "QB": ("epa_per_play", True),
    "RB": ("epa_per_touch", True),
    "WR": ("epa_per_target", True),
    "TE": ("epa_per_target", True),
    "OL": ("snap_share", True),  # no public per-lineman production stat; availability is the honest proxy
    "IDL": ("pressure_rate", True),
    "ED": ("pressure_rate", True),
    "LB": ("play_rate", True),
    "CB": ("passer_rating_allowed", False),
    "S": ("passer_rating_allowed", False),
    "ST": ("snap_share", True),
}

# minimum sample (in the headline metric's denominator) before a player is percentiled; per game played it is small
# early in a season, so the floor is a season total that a starter clears by week 3
MIN_SAMPLE: dict[str, tuple[str, int]] = {
    "QB": ("plays", 60),
    "RB": ("touches", 25),
    "WR": ("targets", 12),
    "TE": ("targets", 10),
    "OL": ("snaps", 60),
    "IDL": ("snaps", 60),
    "ED": ("snaps", 60),
    "LB": ("snaps", 60),
    "CB": ("targets_allowed", 8),
    "S": ("targets_allowed", 6),
    "ST": ("snaps", 10),
}

# how many players the depth chart really starts at each group (top by snap share)
STARTERS: dict[str, int] = {
    "QB": 1,
    "RB": 1,
    "WR": 3,
    "TE": 1,
    "OL": 5,
    "IDL": 2,
    "ED": 2,
    "LB": 2,
    "CB": 3,
    "S": 2,
    "ST": 2,
}

# the age at which a starter at the group is past the typical peak (a need-score input, not a verdict)
AGING: dict[str, int] = {
    "QB": 34,
    "RB": 28,
    "WR": 30,
    "TE": 31,
    "OL": 32,
    "IDL": 31,
    "ED": 31,
    "LB": 30,
    "CB": 30,
    "S": 31,
    "ST": 36,
}


def to_group(label: str | None) -> str | None:
    if label is None:
        return None
    return _MAP.get(label.strip().upper())


def group_expr(*columns: str) -> pl.Expr:
    """First non-null group across the given label columns, in priority order."""
    expr = pl.lit(None, dtype=pl.Utf8)
    for col in reversed(columns):
        mapped = pl.col(col).str.to_uppercase().str.strip_chars().replace_strict(_MAP, default=None)
        expr = pl.coalesce([mapped, expr])
    return expr
