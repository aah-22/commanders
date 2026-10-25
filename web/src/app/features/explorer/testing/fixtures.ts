import { Drive, GameDetail, GameInsights, GamePlays, ImpactPlay, PlayRow, Split, Stat, TeamInsights } from '../../../core/api.service';
import { SUMMARY } from '../../season/testing/fixtures';

export const GAME_ID = '2026_01_NYG_WAS';

function drive(n: number, posteam: string, epa: number, result: string, points: number, qtr: number, secs: number): Drive {
  return {
    drive: n,
    posteam,
    qtr,
    start_seconds: secs,
    start_yardline_100: 75,
    plays: 6,
    yards: 40,
    epa,
    result,
    points,
    points_against: 0,
    first_play_id: n * 100,
    last_play_id: n * 100 + 5,
  };
}

export const GAME: GameDetail = {
  game_id: GAME_ID,
  season: 2026,
  week: 1,
  game_type: 'REG',
  gameday: '2026-09-13',
  gametime: '13:00',
  home_team: 'WAS',
  away_team: 'NYG',
  home_score: 27,
  away_score: 20,
  played: true,
  team: 'WAS',
  prev_game_id: null,
  next_game_id: '2026_02_WAS_DAL',
  drives: [drive(1, 'WAS', 2.4, 'Touchdown', 7, 1, 3600), drive(2, 'NYG', -1.1, 'Punt', 0, 1, 3300), drive(3, 'WAS', -0.4, 'Punt', 0, 2, 2600)],
  win_prob: [
    { play_id: 100, qtr: 1, game_seconds_remaining: 3600, home_wp: 0.55 },
    { play_id: 105, qtr: 1, game_seconds_remaining: 3400, home_wp: 0.7 },
    { play_id: 200, qtr: 1, game_seconds_remaining: 3300, home_wp: 0.72 },
    { play_id: 300, qtr: 2, game_seconds_remaining: 2600, home_wp: 0.66 },
    { play_id: null, qtr: 4, game_seconds_remaining: 0, home_wp: 1 },
  ],
  down_distance: SUMMARY.down_distance,
};

function play(id: number, drive: number, posteam: string, down: number | null, ydstogo: number | null, desc: string, epa: number, extra: Partial<PlayRow> = {}): PlayRow {
  return {
    play_id: id,
    fixed_drive: drive,
    qtr: 1,
    game_seconds_remaining: 3600 - id,
    posteam,
    defteam: posteam === 'WAS' ? 'NYG' : 'WAS',
    down,
    ydstogo,
    yardline_100: 75,
    goal_to_go: 0,
    play_type: down ? 'pass' : 'kickoff',
    desc,
    yards_gained: 8,
    epa,
    wp: 0.6,
    wpa: 0.02,
    success: epa > 0 ? 1 : 0,
    first_down: 0,
    touchdown: 0,
    sack: 0,
    interception: 0,
    fumble_lost: 0,
    penalty: 0,
    complete_pass: 1,
    shotgun: 1,
    no_huddle: 0,
    qb_dropback: 1,
    aborted_play: 0,
    pass_location: 'left',
    run_location: null,
    air_yards: 6,
    yards_after_catch: 2,
    posteam_score: 0,
    defteam_score: 0,
    ...extra,
  };
}

export const PLAYS: GamePlays = {
  game_id: GAME_ID,
  total: 4,
  plays: [
    play(100, 1, 'WAS', null, null, 'Kickoff to the 25', 0),
    play(101, 1, 'WAS', 1, 10, 'Daniels pass short left to McLaurin for 8', 0.6, { charted: 1, qb_location: 'S', is_play_action: 1, n_blitzers: 1, n_defense_box: 6 }),
    play(105, 1, 'WAS', 3, 2, 'Daniels pass deep right to Ertz for 22, TOUCHDOWN', 3.1, { touchdown: 1, first_down: 1, yards_gained: 22 }),
    play(200, 2, 'NYG', 1, 10, 'Jones sacked for -7', -1.4, { sack: 1, yards_gained: -7 }),
  ],
};

export function stat(key: string, label: string, value: number | null, n: number, league: number | null, league_n = 500, kind: Stat['kind'] = 'rate', better: Stat['better'] = 'none', rank: number | null = null, teams: number | null = null): Stat {
  return { key, label, value, n, league, league_n, rank, teams, kind, better };
}

function split(key: string, label: string, n: number, parts: [string, string, number, number][]): Split {
  return { key, label, n, league_n: 1000, parts: parts.map(([k, l, count, league_share]) => ({ key: k, label: l, count, share: n ? count / n : null, league_share })) };
}

/** A pass-heavy, shotgun-heavy WAS offense that was pressured and bad on third down but won 27–20 on a strong second half. */
function was(): TeamInsights {
  return {
    team: 'WAS',
    opponent: 'NYG',
    is_home: true,
    points: 27,
    quarters: [
      { qtr: 1, label: 'Q1', points: 3, plays: 12, epa_per_play: -0.3, success_rate: 0.33 },
      { qtr: 2, label: 'Q2', points: 0, plays: 14, epa_per_play: -0.1, success_rate: 0.4 },
      { qtr: 3, label: 'Q3', points: 14, plays: 16, epa_per_play: 0.15, success_rate: 0.55 },
      { qtr: 4, label: 'Q4', points: 10, plays: 16, epa_per_play: 0.15, success_rate: 0.5 },
    ],
    efficiency: [
      stat('epa_per_play', 'EPA / play', -0.01, 58, 0.02, 7000, 'epa', 'high', 18, 32),
      stat('success_rate', 'Success rate', 0.483, 58, 0.45, 7000, 'rate', 'high', 12, 32),
      stat('explosive_rate', 'Explosive play rate', 0.086, 58, 0.09, 7000, 'rate', 'high', 20, 32),
      stat('pass_epa_per_play', 'Pass EPA / play', -0.05, 42, 0.05, 4000, 'epa', 'high', 22, 32),
      stat('rush_epa_per_play', 'Rush EPA / play', 0.1, 16, -0.05, 3000, 'epa', 'high', 8, 32),
      stat('points_per_drive', 'Points / drive', 2.1, 11, 2.0, 2200, 'number', 'high'),
    ],
    tendencies: [
      stat('pass_rate', 'Dropback rate', 0.724, 58, 0.574),
      stat('proe', 'Pass rate over expected', 0.09, 40, 0.0),
      stat('early_down_pass_rate', 'Early-down dropback rate', 0.7, 40, 0.52),
      stat('shotgun_rate', 'Shotgun snaps (incl. pistol)', 0.91, 58, 0.68),
      stat('play_action_rate', 'Play action', 0.26, 45, 0.25),
      stat('screen_rate', 'Screens', 0.025, 40, 0.106),
      stat('motion_rate', 'Pre-snap motion', 0.5, 58, 0.48),
      stat('pressure_rate_taken', 'Pressured (sack or QB hit)', 0.311, 45, 0.23, 4000, 'rate', 'low'),
      stat('adot', 'Avg. depth of target', 7.9, 40, 7.6, 3500, 'number'),
      stat('rpo_rate', 'RPO', 0.05, 58, 0.06),
    ],
    by_down: [stat('pass_rate_1st', '1st down', 0.65, 26, 0.5), stat('pass_rate_2nd', '2nd down', 0.75, 20, 0.58), stat('pass_rate_3rd', '3rd down', 0.92, 12, 0.8)],
    splits: [
      split('qb_alignment', 'QB alignment', 61, [['under_center', 'Under center', 8, 0.39], ['shotgun', 'Shotgun', 47, 0.57], ['pistol', 'Pistol', 6, 0.04]]),
      split('run_pass', 'Dropback vs run', 58, [['dropback', 'Dropback', 42, 0.57], ['run', 'Designed run', 16, 0.43]]),
      split('pass_location', 'Pass direction', 38, [['left', 'Left', 12, 0.33], ['middle', 'Middle', 10, 0.3], ['right', 'Right', 16, 0.37]]),
      split('box_faced', 'Defenders in the box faced', 0, [['light', '6 or fewer', 0, 0.5], ['seven', '7', 0, 0.35], ['stacked', '8 or more', 0, 0.15]]),
    ],
    situations: [
      stat('third_down_conv', '3rd-down conversions', 0.25, 12, 0.4, 1500, 'rate', 'high'),
      stat('fourth_down_conv', '4th-down conversions', 0.333, 3, 0.55, 200, 'rate', 'high'),
      stat('red_zone_td_rate', 'Red-zone touchdowns', 0.5, 4, 0.55, 400, 'rate', 'high'),
      stat('sack_rate', 'Sacked', 0.089, 45, 0.06, 4000, 'rate', 'low'),
      stat('turnovers', 'Turnovers (incl. on downs)', 1, 11, 1.4, 180, 'count', 'low'),
    ],
    defense: [
      stat('def_epa_per_play', 'EPA / play allowed', 0.21, 60, 0.02, 7000, 'epa', 'low', 28, 32),
      stat('def_success_rate', 'Success rate allowed', 0.533, 60, 0.45, 7000, 'rate', 'low', 27, 32),
      stat('pressure_rate', 'Pressure rate (sack or hit)', 0.15, 34, 0.23, 4000, 'rate', 'high'),
      stat('blitz_rate', 'Blitz rate', 0.3, 34, 0.27),
      stat('light_box_rate', 'Light boxes shown (6 or fewer)', null, 0, 0.5),
    ],
    defense_splits: [split('box_shown', 'Defenders in the box', 0, [['light', '6 or fewer', 0, 0.5], ['seven', '7', 0, 0.35], ['stacked', '8 or more', 0, 0.15]])],
    players: [
      { gsis_id: '00-Q1', name: 'Jayden Daniels', position: 'QB', team: 'WAS', plays: 46, as_passer: 42, as_rusher: 4, as_receiver: 0, yards: 310, epa: -0.5, wpa: -0.12, big_plays: 9 },
      { gsis_id: '00-W1', name: 'Terry McLaurin', position: 'WR', team: 'WAS', plays: 9, as_passer: 0, as_rusher: 0, as_receiver: 9, yards: 96, epa: 2.4, wpa: 0.11, big_plays: 3 },
    ],
  };
}

function nyg(): TeamInsights {
  const t = was();
  return {
    ...t,
    team: 'NYG',
    opponent: 'WAS',
    is_home: false,
    points: 20,
    quarters: [
      { qtr: 1, label: 'Q1', points: 13, plays: 15, epa_per_play: 0.3, success_rate: 0.6 },
      { qtr: 2, label: 'Q2', points: 7, plays: 16, epa_per_play: 0.2, success_rate: 0.5 },
      { qtr: 3, label: 'Q3', points: 0, plays: 14, epa_per_play: -0.2, success_rate: 0.3 },
      { qtr: 4, label: 'Q4', points: 0, plays: 15, epa_per_play: -0.1, success_rate: 0.4 },
    ],
    efficiency: t.efficiency.map((s) => ({ ...s, value: s.key === 'epa_per_play' ? 0.21 : s.value, rank: null, teams: null })),
    tendencies: t.tendencies.map((s) => ({ ...s, value: s.key === 'pass_rate' ? 0.55 : s.value })),
    players: [{ gsis_id: '00-N1', name: 'Jaxson Dart', position: 'QB', team: 'NYG', plays: 30, as_passer: 28, as_rusher: 2, as_receiver: 0, yards: 220, epa: 1.1, wpa: 0.08, big_plays: 5 }],
  };
}

function swing(play_id: number, posteam: string, qtr: number, secs: number, desc: string, wp: number, wpa: number, extra: Partial<ImpactPlay> = {}): ImpactPlay {
  const home = posteam === 'WAS';
  const before = home ? wp : 1 - wp;
  return {
    play_id,
    drive: 9,
    qtr,
    game_seconds_remaining: secs,
    posteam,
    defteam: home ? 'NYG' : 'WAS',
    down: 4,
    ydstogo: 3,
    yardline_100: 24,
    goal_to_go: 0,
    play_type: 'pass',
    desc,
    yards_gained: 0,
    epa: -3,
    wpa,
    home_wp_before: before,
    home_wp_after: before + (home ? wpa : -wpa),
    touchdown: 0,
    interception: 0,
    fumble_lost: 0,
    sack: 0,
    penalty: 0,
    fourth_down: true,
    posteam_score: 17,
    defteam_score: 23,
    ...extra,
  };
}

export const INSIGHTS: GameInsights = {
  game_id: GAME_ID,
  season: 2026,
  week: 1,
  home_team: 'WAS',
  away_team: 'NYG',
  home_score: 27,
  away_score: 20,
  played: true,
  team: 'WAS',
  opponent: 'NYG',
  league_through_week: 2,
  league_teams: 32,
  charted: true,
  teams: [was(), nyg()],
  impact_plays: [
    swing(905, 'WAS', 4, 120, '(2:00) (Shotgun) 5-J.Daniels pass incomplete deep right to 13-T.Burks (6-M.Mustapha).', 0.23, -0.22),
    swing(410, 'NYG', 2, 1900, '(1:40) 6-J.Dart pass deep left to 1-M.Nabers for 35 yards, TOUCHDOWN.', 0.6, 0.18, { touchdown: 1, drive: 4, down: 2, ydstogo: 8, yardline_100: 35, epa: 4.1 }),
  ],
  scoring: [
    { play_id: 105, qtr: 1, game_seconds_remaining: 3400, team: 'WAS', desc: 'Daniels pass deep right to Ertz for 22, TOUCHDOWN', points: 7, home_score: 7, away_score: 0 },
    { play_id: 410, qtr: 2, game_seconds_remaining: 1900, team: 'NYG', desc: 'Dart pass deep left to Nabers for 35 yards, TOUCHDOWN.', points: 7, home_score: 7, away_score: 7 },
  ],
};
