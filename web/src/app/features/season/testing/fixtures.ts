import { GameRow, LeagueSummary, SeasonGames, SeasonSummary, TeamGameSummary, TeamSeasonAggregate } from '../../../core/api.service';

function week(w: number, opponent: string, result: 'W' | 'L', pf: number, pa: number, off: number, def: number): TeamGameSummary {
  return {
    season: 2026,
    week: w,
    team: 'WAS',
    game_id: `2026_0${w}_WAS_${opponent}`,
    gameday: `2026-09-${12 + 7 * w}`,
    opponent,
    is_home: w % 2 === 0,
    game_type: 'REG',
    points_for: pf,
    points_against: pa,
    result,
    week_teams: 32,
    off_plays: 66,
    off_epa_per_play: off,
    off_success_rate: 0.47,
    off_explosive_rate: 0.08,
    off_proe: -0.04,
    off_pass_epa_per_play: off + 0.02,
    off_rush_epa_per_play: off - 0.02,
    off_third_down_conv: 0.4,
    off_red_zone_td_rate: 0.5,
    off_points_per_drive: 2.0,
    off_turnovers: 1,
    off_epa_per_play_rank: 12,
    off_success_rate_rank: 10,
    def_plays: 70,
    def_epa_per_play: def,
    def_success_rate: 0.46,
    def_explosive_rate: 0.1,
    def_points_per_drive: 3.0,
    def_turnovers: 1,
    def_epa_per_play_rank: 26,
  };
}

function team(t: string, off: number, def: number, offRank: number, defRank: number): TeamSeasonAggregate {
  return {
    team: t,
    games: 2,
    off_epa_per_play: off,
    off_success_rate: 0.45,
    off_explosive_rate: 0.08,
    off_proe: 0,
    off_pass_epa_per_play: off,
    off_rush_epa_per_play: off,
    off_points_per_drive: 2,
    def_epa_per_play: def,
    def_success_rate: 0.45,
    def_explosive_rate: 0.08,
    def_pass_epa_per_play: def,
    def_rush_epa_per_play: def,
    def_points_per_drive: 2,
    ranks: { off_epa_per_play: offRank, def_epa_per_play: defRank },
  };
}

export const WEEKS: TeamGameSummary[] = [week(1, 'PHI', 'L', 22, 24, 0.06, 0.071), week(2, 'DAL', 'L', 20, 37, 0.103, 0.227)];

export const SUMMARY: SeasonSummary = {
  season: 2026,
  team: 'WAS',
  through_week: 2,
  league_teams: 32,
  standing: {
    season: 2026,
    week: 2,
    team: 'WAS',
    conf: 'NFC',
    division: 'NFC East',
    wins: 0,
    losses: 2,
    ties: 0,
    games_played: 2,
    pf: 42,
    pa: 61,
    point_diff: -19,
    win_pct: 0,
    pythag_win_pct: 0.292,
    div_rank: 4,
    conf_rank: 15,
  },
  weeks: WEEKS,
  aggregate: team('WAS', 0.081, 0.151, 11, 26),
  league_weekly: [
    { week: 1, teams: 32, off_epa_p25: -0.1, off_epa_median: 0.0, off_epa_p75: 0.1, def_epa_p25: -0.1, def_epa_median: 0.0, def_epa_p75: 0.1 },
    { week: 2, teams: 32, off_epa_p25: -0.12, off_epa_median: 0.01, off_epa_p75: 0.11, def_epa_p25: -0.11, def_epa_median: 0.01, def_epa_p75: 0.12 },
  ],
  next_game: { game_id: '2026_03_SEA_WAS', week: 3, opponent: 'SEA', is_home: true, gameday: '2026-09-27', gametime: '13:00' },
  down_distance: [1, 2, 3].flatMap((down) =>
    (['short', 'mid', 'long', 'xlong'] as const).map((bucket) => ({
      down,
      bucket,
      team_rate: bucket === 'short' ? 0.5 : 0.45,
      team_n: bucket === 'short' ? 2 : 53,
      league_rate: 0.42,
      league_n: 1516,
    })),
  ),
};

export const LEAGUE: LeagueSummary = {
  season: 2026,
  through_week: 2,
  teams: [team('WAS', 0.081, 0.151, 11, 26), team('PHI', 0.2, -0.05, 1, 2), team('DAL', 0.15, 0.1, 3, 20), team('NYG', -0.1, 0.05, 30, 12)],
};

const GAME_ROWS: GameRow[] = [
  ...WEEKS.map((w) => ({
    game_id: w.game_id,
    week: w.week,
    game_type: 'REG',
    gameday: w.gameday,
    gametime: '13:00',
    opponent: w.opponent as string,
    is_home: w.is_home as boolean,
    points_for: w.points_for,
    points_against: w.points_against,
    result: w.result,
    summary: w,
  })),
  { game_id: '2026_03_SEA_WAS', week: 3, game_type: 'REG', gameday: '2026-09-27', gametime: '13:00', opponent: 'SEA', is_home: true, points_for: null, points_against: null, result: null, summary: null },
];

export const GAMES: SeasonGames = { season: 2026, team: 'WAS', games: GAME_ROWS };

export const EMPTY_SUMMARY: SeasonSummary = {
  ...SUMMARY,
  through_week: null,
  standing: null,
  weeks: [],
  aggregate: null,
  league_weekly: [],
  down_distance: [],
};
