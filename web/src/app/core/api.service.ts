import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface Freshness {
  season: number;
  team: string;
  last_ingest: string | null;
  through_week: number | null;
}

/** One row of gm.team_game_summary (every off_/def_ metric is nullable when its denominator was zero). */
export interface TeamGameSummary {
  season: number;
  week: number;
  team: string;
  game_id: string;
  gameday: string | null;
  opponent: string | null;
  is_home: boolean | null;
  game_type: string | null;
  points_for: number | null;
  points_against: number | null;
  result: 'W' | 'L' | 'T' | null;
  week_teams: number | null;
  off_plays: number | null;
  off_epa_per_play: number | null;
  off_success_rate: number | null;
  off_explosive_rate: number | null;
  off_proe: number | null;
  off_pass_epa_per_play: number | null;
  off_rush_epa_per_play: number | null;
  off_third_down_conv: number | null;
  off_red_zone_td_rate: number | null;
  off_points_per_drive: number | null;
  off_turnovers: number | null;
  off_epa_per_play_rank: number | null;
  off_success_rate_rank: number | null;
  def_plays: number | null;
  def_epa_per_play: number | null;
  def_success_rate: number | null;
  def_explosive_rate: number | null;
  def_points_per_drive: number | null;
  def_turnovers: number | null;
  def_epa_per_play_rank: number | null;
  [metric: string]: number | string | boolean | null | undefined;
}

export interface Standing {
  season: number;
  week: number;
  team: string;
  conf: string | null;
  division: string | null;
  wins: number;
  losses: number;
  ties: number;
  games_played: number;
  pf: number;
  pa: number;
  point_diff: number;
  win_pct: number | null;
  pythag_win_pct: number | null;
  div_rank: number | null;
  conf_rank: number | null;
}

export interface TeamSeasonAggregate {
  team: string;
  games: number;
  off_epa_per_play: number | null;
  off_success_rate: number | null;
  off_explosive_rate: number | null;
  off_proe: number | null;
  off_pass_epa_per_play: number | null;
  off_rush_epa_per_play: number | null;
  off_points_per_drive: number | null;
  def_epa_per_play: number | null;
  def_success_rate: number | null;
  def_explosive_rate: number | null;
  def_pass_epa_per_play: number | null;
  def_rush_epa_per_play: number | null;
  def_points_per_drive: number | null;
  ranks: Record<string, number>;
}

export interface NextGame {
  game_id: string;
  week: number;
  opponent: string;
  is_home: boolean;
  gameday: string | null;
  gametime: string | null;
}

export interface LeagueWeek {
  week: number;
  teams: number;
  off_epa_p25: number | null;
  off_epa_median: number | null;
  off_epa_p75: number | null;
  def_epa_p25: number | null;
  def_epa_median: number | null;
  def_epa_p75: number | null;
}

export type DistanceBucket = 'short' | 'mid' | 'long' | 'xlong';

export interface DownDistanceCell {
  down: number;
  bucket: DistanceBucket;
  team_rate: number | null;
  team_n: number;
  league_rate: number | null;
  league_n: number;
}

export interface SeasonSummary {
  season: number;
  team: string;
  through_week: number | null;
  league_teams: number;
  standing: Standing | null;
  weeks: TeamGameSummary[];
  aggregate: TeamSeasonAggregate | null;
  league_weekly: LeagueWeek[];
  next_game: NextGame | null;
  down_distance: DownDistanceCell[];
}

export interface LeagueSummary {
  season: number;
  through_week: number | null;
  teams: TeamSeasonAggregate[];
}

export interface GameRow {
  game_id: string;
  week: number;
  game_type: string;
  gameday: string | null;
  gametime: string | null;
  opponent: string;
  is_home: boolean;
  points_for: number | null;
  points_against: number | null;
  result: 'W' | 'L' | 'T' | null;
  summary: TeamGameSummary | null;
}

export interface SeasonGames {
  season: number;
  team: string;
  games: GameRow[];
}

/** One offensive possession, folded from the plays; `points` is what the offense scored on it. */
export interface Drive {
  drive: number;
  posteam: string | null;
  qtr: number | null;
  start_seconds: number | null;
  start_yardline_100: number | null;
  plays: number;
  yards: number;
  epa: number | null;
  result: string | null;
  points: number | null;
  points_against: number | null;
  first_play_id: number;
  last_play_id: number;
}

/** Home team's win probability before the play; the last point (play_id null) is the final result. */
export interface WinProbPoint {
  play_id: number | null;
  qtr: number | null;
  game_seconds_remaining: number;
  home_wp: number;
}

export interface GameDetail {
  game_id: string;
  season: number;
  week: number;
  game_type: string;
  gameday: string | null;
  gametime: string | null;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  played: boolean;
  team: string;
  prev_game_id: string | null;
  next_game_id: string | null;
  drives: Drive[];
  win_prob: WinProbPoint[];
  down_distance: DownDistanceCell[];
}

export interface PlayRow {
  play_id: number;
  fixed_drive: number | null;
  qtr: number | null;
  game_seconds_remaining: number | null;
  half_seconds_remaining?: number | null;
  posteam: string | null;
  defteam: string | null;
  down: number | null;
  ydstogo: number | null;
  yardline_100: number | null;
  goal_to_go: number | null;
  play_type: string | null;
  desc: string | null;
  yards_gained: number | null;
  epa: number | null;
  wp: number | null;
  wpa: number | null;
  xpass?: number | null;
  success: number | null;
  first_down: number | null;
  touchdown: number | null;
  sack: number | null;
  qb_hit?: number | null;
  qb_scramble?: number | null;
  interception: number | null;
  fumble_lost: number | null;
  penalty: number | null;
  complete_pass: number | null;
  shotgun: number | null;
  no_huddle: number | null;
  qb_dropback: number | null;
  aborted_play: number | null;
  pass_location: string | null;
  run_location: string | null;
  air_yards: number | null;
  yards_after_catch: number | null;
  series?: number | null;
  passer_player_id?: string | null;
  rusher_player_id?: string | null;
  receiver_player_id?: string | null;
  posteam_score: number | null;
  defteam_score: number | null;
  /** FTN charting; null when the play has no charting row (special teams, or a week not charted yet). */
  charted?: number | null;
  qb_location?: 'U' | 'S' | 'P' | string | null;
  n_defense_box?: number | null;
  n_pass_rushers?: number | null;
  n_blitzers?: number | null;
  read_thrown?: string | null;
  is_play_action?: number | null;
  is_screen_pass?: number | null;
  is_rpo?: number | null;
  is_motion?: number | null;
  is_qb_out_of_pocket?: number | null;
  is_drop?: number | null;
  is_interception_worthy?: number | null;
  is_throw_away?: number | null;
}

export type PlayKind = 'all' | 'scrimmage' | 'pass' | 'run' | 'special';

/** One-tap narrowings of the play list (see api/schemas/game.py `PlayTag`). */
export type PlayTag =
  | 'play_action'
  | 'screen'
  | 'rpo'
  | 'motion'
  | 'blitz'
  | 'light_box'
  | 'pressure'
  | 'scramble'
  | 'explosive'
  | 'no_huddle'
  | 'penalty'
  | 'big_swing';

/** The explorer's filters; every field optional, mirrored in the page URL's query string. */
export interface PlayFilters {
  posteam?: string;
  down?: number;
  distance?: DistanceBucket;
  rz?: boolean;
  drive?: number;
  type?: PlayKind;
  /** 1–4, or 5 for overtime. */
  qtr?: number;
  tag?: PlayTag;
}

export interface GamePlays {
  game_id: string;
  total: number;
  plays: PlayRow[];
}

/**
 * One number on the insights page: the team's value in this game, the plays behind it, the league's season-to-date
 * value for the same definition and, where the week ranks it, the rank. `kind` says how to print it; `better` whether
 * higher is good, bad, or neither (a tendency such as a pass rate has no valence).
 */
export interface Stat {
  key: string;
  label: string;
  value: number | null;
  n: number;
  league: number | null;
  league_n: number;
  rank: number | null;
  teams: number | null;
  kind: 'rate' | 'epa' | 'count' | 'number';
  better: 'high' | 'low' | 'none';
}

export interface Share {
  key: string;
  label: string;
  count: number;
  share: number | null;
  league_share: number | null;
}

/** A part-to-whole breakdown (QB alignment, pass direction, target depth, box counts) with the league's shares. */
export interface Split {
  key: string;
  label: string;
  n: number;
  league_n: number;
  parts: Share[];
}

export interface QuarterLine {
  qtr: number;
  label: string;
  points: number | null;
  plays: number;
  epa_per_play: number | null;
  success_rate: number | null;
}

export interface ImpactPlayer {
  gsis_id: string;
  name: string | null;
  position: string | null;
  team: string;
  plays: number;
  as_passer: number;
  as_rusher: number;
  as_receiver: number;
  yards: number;
  epa: number | null;
  wpa: number | null;
  big_plays: number;
}

export interface TeamInsights {
  team: string;
  opponent: string;
  is_home: boolean;
  points: number | null;
  quarters: QuarterLine[];
  efficiency: Stat[];
  tendencies: Stat[];
  by_down: Stat[];
  splits: Split[];
  situations: Stat[];
  defense: Stat[];
  defense_splits: Split[];
  players: ImpactPlayer[];
}

export interface ImpactPlay {
  play_id: number;
  drive: number | null;
  qtr: number | null;
  game_seconds_remaining: number | null;
  posteam: string | null;
  defteam: string | null;
  down: number | null;
  ydstogo: number | null;
  yardline_100: number | null;
  goal_to_go: number | null;
  play_type: string | null;
  desc: string | null;
  yards_gained: number | null;
  epa: number | null;
  wpa: number | null;
  home_wp_before: number | null;
  home_wp_after: number | null;
  touchdown: number | null;
  interception: number | null;
  fumble_lost: number | null;
  sack: number | null;
  penalty: number | null;
  fourth_down: boolean;
  posteam_score: number | null;
  defteam_score: number | null;
}

/** A play that changed the score; a touchdown's row includes the try that followed it. */
export interface ScoringPlay {
  play_id: number;
  qtr: number | null;
  game_seconds_remaining: number | null;
  team: string;
  desc: string | null;
  points: number;
  home_score: number;
  away_score: number;
}

export interface GameInsights {
  game_id: string;
  season: number;
  week: number;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  played: boolean;
  /** The focus team, teams[0]; the opponent is teams[1]. */
  team: string;
  opponent: string;
  league_through_week: number | null;
  league_teams: number;
  /** FTN charting rows exist for this game (play action, screens, alignment, box and blitz counts). */
  charted: boolean;
  teams: TeamInsights[];
  /** The biggest win-probability swings, largest first. */
  impact_plays: ImpactPlay[];
  /** In game order. */
  scoring: ScoringPlay[];
}

/** One arrival with this season's production and the value model's expectation; `grade` is A–F on the gap. */
export interface AcquisitionCard {
  gsis_id: string;
  name: string | null;
  position: string | null;
  pos_group: string | null;
  how: string;
  date: string | null;
  from_team: string | null;
  draft_round: number | null;
  draft_pick: number | null;
  arrival_season: number;
  current_team: string | null;
  apy: number | null;
  contract_years: number | null;
  guaranteed: number | null;
  year_signed: number | null;
  years_left: number | null;
  age: number | null;
  games: number | null;
  snaps: number | null;
  snap_share: number | null;
  metric: string | null;
  production: number | null;
  production_pct: number | null;
  qualified: boolean | null;
  cost_pct: number | null;
  graded_seasons: number[];
  tenure_pct: number | null;
  expected_pct: number | null;
  basis: 'model' | 'cost' | 'mixed';
  value_gap: number | null;
  grade: string | null;
  run_id: string | null;
  model_version: string | null;
}

export interface Acquisitions {
  season: number;
  team: string;
  since: number;
  cards: AcquisitionCard[];
}

export interface Starter {
  gsis_id: string;
  name: string | null;
  position: string | null;
  age: number | null;
  snap_share: number | null;
  production_pct: number | null;
  years_left: number | null;
  apy: number | null;
}

export interface NeedGroup {
  pos_group: string;
  starters: number;
  starter_pct: number | null;
  starters_expiring: number;
  starters_aging: number;
  avg_age: number | null;
  contract_years_left: number | null;
  depth: number;
  need_score: number;
  need_rank: number | null;
  starter_list: Starter[];
}

export interface Need {
  season: number;
  team: string;
  groups: NeedGroup[];
}

export interface Target {
  gsis_id: string;
  name: string | null;
  team: string | null;
  position: string | null;
  pos_group: string | null;
  age: number | null;
  games: number | null;
  production_pct: number | null;
  projected_pct: number | null;
  projection_run_id: string | null;
  apy: number | null;
  years_left: number | null;
  reason: string | null;
  need_score: number | null;
  score: number;
  run_id: string | null;
  version: string | null;
}

export interface Targets {
  season: number;
  team: string;
  position: string | null;
  live: boolean;
  scored_at: string | null;
  targets: Target[];
}

export interface ModelOutputSummary {
  model: string;
  season: number;
  version: string | null;
  run_id: string | null;
  rows: number;
  scored_at: string | null;
}

export interface JobSummary {
  kind: string;
  status: string;
  season: number | null;
  finished_at: string;
  detail: Record<string, unknown>;
}

export interface Models {
  experiment: string;
  tracking: string;
  outputs: ModelOutputSummary[];
  jobs: JobSummary[];
}

/** Thin typed client over the read-only API; nginx proxies /api/ to the FastAPI service, so paths stay relative. */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api';

  gmAcquisitions(): Observable<Acquisitions> {
    return this.http.get<Acquisitions>(`${this.base}/v1/gm/acquisitions`);
  }

  gmNeed(): Observable<Need> {
    return this.http.get<Need>(`${this.base}/v1/gm/need`);
  }

  gmTargets(position: string | null = null): Observable<Targets> {
    const params = position ? new HttpParams().set('position', position) : new HttpParams();
    return this.http.get<Targets>(`${this.base}/v1/gm/targets`, { params });
  }

  models(): Observable<Models> {
    return this.http.get<Models>(`${this.base}/v1/models`);
  }

  game(gameId: string): Observable<GameDetail> {
    return this.http.get<GameDetail>(`${this.base}/v1/games/${gameId}`);
  }

  gamePlays(gameId: string, filters: PlayFilters = {}): Observable<GamePlays> {
    let params = new HttpParams();
    if (filters.posteam) params = params.set('posteam', filters.posteam);
    if (filters.down) params = params.set('down', filters.down);
    if (filters.distance) params = params.set('distance', filters.distance);
    if (filters.rz) params = params.set('rz', 'true');
    if (filters.drive) params = params.set('drive', filters.drive);
    if (filters.type && filters.type !== 'all') params = params.set('type', filters.type);
    if (filters.qtr) params = params.set('qtr', filters.qtr);
    if (filters.tag) params = params.set('tag', filters.tag);
    return this.http.get<GamePlays>(`${this.base}/v1/games/${gameId}/plays`, { params });
  }

  gameInsights(gameId: string): Observable<GameInsights> {
    return this.http.get<GameInsights>(`${this.base}/v1/games/${gameId}/insights`);
  }

  freshness(): Observable<Freshness> {
    return this.http.get<Freshness>(`${this.base}/v1/meta/freshness`);
  }

  seasonSummary(season: number): Observable<SeasonSummary> {
    return this.http.get<SeasonSummary>(`${this.base}/v1/season/${season}/summary`);
  }

  seasonLeague(season: number): Observable<LeagueSummary> {
    return this.http.get<LeagueSummary>(`${this.base}/v1/season/${season}/league`);
  }

  seasonGames(season: number): Observable<SeasonGames> {
    return this.http.get<SeasonGames>(`${this.base}/v1/season/${season}/games`);
  }
}
