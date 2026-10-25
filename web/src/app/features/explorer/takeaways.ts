import { GameInsights, ImpactPlay, QuarterLine, Stat, TeamInsights } from '../../core/api.service';
import { cleanDesc, clock, downDistance, fmtEpa, ppGap, yardline } from '../../core/format';

/** The page's section anchors, in page order. */
export type SectionId = 'story' | 'matchup' | 'drives' | 'offense' | 'defense' | 'situations' | 'big-plays' | 'plays';

export interface Takeaway {
  text: string;
  section: SectionId;
}

const MIN_RATE_N = 10; // a rate on fewer plays than this says nothing about a game

function stat(list: Stat[], key: string): Stat | undefined {
  return list.find((s) => s.key === key);
}

function pct(x: number): string {
  return `${Math.round(100 * x)}%`;
}

/** A rate with enough plays behind it and a league figure to compare with. */
function usable(s: Stat | undefined): s is Stat & { value: number; league: number } {
  return !!s && s.value != null && s.league != null && s.n >= MIN_RATE_N;
}

function ofN(s: Stat): string {
  return `${Math.round((s.value ?? 0) * s.n)} of ${s.n}`;
}

/** Plays-weighted EPA / play and points over a set of quarters. */
function half(qs: QuarterLine[]): { epa: number | null; points: number; plays: number } {
  const plays = qs.reduce((a, q) => a + q.plays, 0);
  const epa = plays ? qs.reduce((a, q) => a + (q.epa_per_play ?? 0) * q.plays, 0) / plays : null;
  return { epa, points: qs.reduce((a, q) => a + (q.points ?? 0), 0), plays };
}

/** The focus team's win chance before and after a play, whichever side it is on. */
export function focusWp(p: ImpactPlay, focusIsHome: boolean): { before: number | null; after: number | null } {
  const flip = (x: number | null) => (x == null ? null : focusIsHome ? x : 1 - x);
  return { before: flip(p.home_wp_before), after: flip(p.home_wp_after) };
}

function passer(t: TeamInsights): string {
  return t.players.find((p) => p.as_passer >= 5)?.name ?? `${t.team}'s quarterback`;
}

/**
 * Three to five plain sentences about the game, generated from the numbers on the page: the result and the offenses'
 * EPA first, then the biggest departures from the league (a pass lean, the alignment, play action, screens, motion,
 * pressure, third down, the red zone), the second-half swing and the biggest win-probability play, ranked by how far
 * they stray and kept only when the sample supports them.
 */
export function takeaways(ins: GameInsights): Takeaway[] {
  const [f, o] = ins.teams;
  if (!f || !o) return [];
  const out: Takeaway[] = [];
  const fs = f.points ?? 0;
  const os = o.points ?? 0;
  const verb = !ins.played ? 'play' : fs > os ? 'beat' : fs < os ? 'lost to' : 'tied';
  const where = f.is_home ? 'vs' : 'at';
  const fEpa = stat(f.efficiency, 'epa_per_play');
  const oEpa = stat(o.efficiency, 'epa_per_play');
  let result = ins.played ? `${f.team} ${verb} ${o.team} ${fs}–${os} ${where === 'vs' ? 'at home' : 'on the road'}.` : `${f.team} ${where} ${o.team}, not played yet.`;
  if (fEpa?.value != null && oEpa?.value != null) {
    const league = fEpa.league != null ? ` (NFL avg ${fmtEpa(fEpa.league, 2)})` : '';
    result += ` Offense ${fmtEpa(fEpa.value, 2)} EPA / play${league}; ${o.team} ${fmtEpa(oEpa.value, 2)}.`;
  }
  out.push({ text: result, section: 'matchup' });
  if (!ins.played) return out;

  const ranked: { score: number; t: Takeaway }[] = [];
  const add = (score: number, text: string, section: SectionId) => ranked.push({ score, t: { text, section } });

  const pass = stat(f.tendencies, 'pass_rate');
  if (usable(pass) && Math.abs(pass.value - pass.league) >= 0.08) {
    const proe = stat(f.tendencies, 'proe');
    const proeText = proe?.value != null && proe.n >= 5 ? `; pass rate over expected ${proe.value > 0 ? '+' : ''}${Math.round(100 * proe.value)}% on neutral downs` : '';
    const lean = pass.value > pass.league ? 'Threw' : 'Handed off more than most: dropped back';
    add(Math.abs(pass.value - pass.league) * 100, `${lean} on ${pct(pass.value)} of snaps (${ofN(pass)}), ${ppGap(pass.value, pass.league)} vs the league rate${proeText}.`, 'offense');
  }

  const align = f.splits.find((s) => s.key === 'qb_alignment');
  const uc = align?.parts.find((p) => p.key === 'under_center');
  if (align && uc && uc.share != null && uc.league_share != null && align.n >= MIN_RATE_N && Math.abs(uc.share - uc.league_share) >= 0.15) {
    const sg = align.parts.find((p) => p.key === 'shotgun');
    const pistol = align.parts.find((p) => p.key === 'pistol');
    const rest = [sg?.share != null ? `shotgun ${pct(sg.share)}` : '', pistol?.share != null ? `pistol ${pct(pistol.share)}` : ''].filter(Boolean).join(', ');
    add(Math.abs(uc.share - uc.league_share) * 100, `Lined up under center on ${pct(uc.share)} of snaps (${uc.count} of ${align.n}), ${ppGap(uc.share, uc.league_share)} vs the league; ${rest}.`, 'offense');
  }

  for (const [key, what, unit] of [
    ['play_action_rate', 'Used play action on', 'dropbacks'],
    ['screen_rate', 'Called screens on', 'passes'],
    ['motion_rate', 'Used pre-snap motion on', 'snaps'],
  ] as const) {
    const s = stat(f.tendencies, key);
    if (usable(s) && Math.abs(s.value - s.league) >= 0.08) {
      add(Math.abs(s.value - s.league) * 100, `${what} ${pct(s.value)} of ${unit} (${ofN(s)}), ${ppGap(s.value, s.league)} vs the league.`, 'offense');
    }
  }

  const pressured = stat(f.tendencies, 'pressure_rate_taken');
  const sacks = stat(f.situations, 'sack_rate');
  const sackCount = sacks?.value != null ? Math.round(sacks.value * sacks.n) : 0;
  if ((usable(pressured) && pressured.value >= pressured.league + 0.08) || sackCount >= 4) {
    const rate = usable(pressured) ? `pressured on ${pct(pressured.value)} of dropbacks (${ofN(pressured)}; NFL ${pct(pressured.league)})` : `pressured often`;
    add((usable(pressured) ? (pressured.value - pressured.league) * 100 : 0) + sackCount * 3, `${passer(f)} was ${rate}, sacked ${sackCount} time${sackCount === 1 ? '' : 's'}.`, 'defense');
  }

  const third = stat(f.situations, 'third_down_conv');
  if (third?.value != null && third.league != null && third.n >= 5 && Math.abs(third.value - third.league) >= 0.15) {
    add(Math.abs(third.value - third.league) * 100, `Converted ${ofN(third)} third downs (${pct(third.value)}; NFL ${pct(third.league)}).`, 'situations');
  }
  const rz = stat(f.situations, 'red_zone_td_rate');
  if (rz?.value != null && rz.league != null && rz.n >= 3 && Math.abs(rz.value - rz.league) >= 0.15) {
    add(Math.abs(rz.value - rz.league) * 100, `Scored touchdowns on ${ofN(rz)} red-zone trips (${pct(rz.value)}; NFL ${pct(rz.league)}).`, 'situations');
  }

  const h1 = half(f.quarters.filter((q) => q.qtr <= 2));
  const h2 = half(f.quarters.filter((q) => q.qtr >= 3));
  const oh2 = half(o.quarters.filter((q) => q.qtr >= 3));
  if (h1.plays >= 5 && h2.plays >= 5 && h1.epa != null && h2.epa != null) {
    const swing = h2.epa - h1.epa;
    const outscored = fs < os && h2.points > oh2.points;
    if (Math.abs(swing) >= 0.25 || outscored) {
      const scoreline = outscored ? `Outscored ${o.team} ${h2.points}–${oh2.points} after halftime but the ${h1.points}–${(o.points ?? 0) - oh2.points} halftime deficit held` : `${swing > 0 ? 'Better' : 'Worse'} after halftime`;
      add(Math.abs(swing) * 100 + (outscored ? 10 : 0), `${scoreline}: ${fmtEpa(h2.epa, 2)} EPA / play in the second half after ${fmtEpa(h1.epa, 2)} in the first.`, 'drives');
    }
  }

  const big = ins.impact_plays[0];
  if (big?.wpa != null) {
    const { before, after } = focusWp(big, f.is_home);
    const wp = before != null && after != null ? `; ${f.team} win chance ${pct(before)} → ${pct(after)}` : '';
    const where = big.down != null ? `${downDistance(big.down, big.ydstogo, big.goal_to_go)} at ${yardline(big.yardline_100)}` : (big.play_type ?? 'play');
    const what = (cleanDesc(big.desc) || big.play_type || 'play').replace(/\.$/, '');
    add(Math.abs(big.wpa) * 100 + 5, `The biggest swing: ${clock(big.qtr, big.game_seconds_remaining)}, ${where}, ${what}${wp}.`, 'big-plays');
  }

  ranked.sort((a, b) => b.score - a.score);
  return out.concat(ranked.slice(0, 4).map((r) => r.t));
}
