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
  success: number | null;
  first_down: number | null;
  touchdown: number | null;
  sack: number | null;
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
  posteam_score: number | null;
  defteam_score: number | null;
}

export type PlayKind = 'all' | 'scrimmage' | 'pass' | 'run' | 'special';

/** The explorer's filters; every field optional, mirrored in the page URL's query string. */
export interface PlayFilters {
  posteam?: string;
  down?: number;
  distance?: DistanceBucket;
  rz?: boolean;
  drive?: number;
  type?: PlayKind;
}

export interface GamePlays {
  game_id: string;
  total: number;
  plays: PlayRow[];
}

/** Thin typed client over the read-only API; nginx proxies /api/ to the FastAPI service, so paths stay relative. */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api';

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
    return this.http.get<GamePlays>(`${this.base}/v1/games/${gameId}/plays`, { params });
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
