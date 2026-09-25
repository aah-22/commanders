import { HttpClient } from '@angular/common/http';
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

/** Thin typed client over the read-only API; nginx proxies /api/ to the FastAPI service, so paths stay relative. */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api';

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
