import { Drive, GameDetail, GamePlays, PlayRow } from '../../../core/api.service';
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
    play(101, 1, 'WAS', 1, 10, 'Daniels pass short left to McLaurin for 8', 0.6),
    play(105, 1, 'WAS', 3, 2, 'Daniels pass deep right to Ertz for 22, TOUCHDOWN', 3.1, { touchdown: 1, first_down: 1, yards_gained: 22 }),
    play(200, 2, 'NYG', 1, 10, 'Jones sacked for -7', -1.4, { sack: 1, yards_gained: -7 }),
  ],
};
