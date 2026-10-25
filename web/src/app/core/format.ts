/** Number formatting shared by the tiles, charts and tables. Nulls print as an en dash. */

export function fmtEpa(x: number | null | undefined, digits = 3): string {
  if (x === null || x === undefined || Number.isNaN(x)) return '–';
  const s = x.toFixed(digits);
  return x > 0 ? `+${s}` : s;
}

export function fmtPct(x: number | null | undefined, digits = 0): string {
  if (x === null || x === undefined || Number.isNaN(x)) return '–';
  return `${(100 * x).toFixed(digits)}%`;
}

export function fmtSignedPct(x: number | null | undefined, digits = 1): string {
  if (x === null || x === undefined || Number.isNaN(x)) return '–';
  const s = `${(100 * x).toFixed(digits)}%`;
  return x > 0 ? `+${s}` : s;
}

export function fmtNum(x: number | null | undefined, digits = 2): string {
  if (x === null || x === undefined || Number.isNaN(x)) return '–';
  return x.toFixed(digits);
}

export function ordinal(n: number | null | undefined): string {
  if (n === null || n === undefined) return '–';
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${n}th`;
  const suffix = { 1: 'st', 2: 'nd', 3: 'rd' }[n % 10] ?? 'th';
  return `${n}${suffix}`;
}

export function record(wins: number, losses: number, ties: number): string {
  return ties ? `${wins}–${losses}–${ties}` : `${wins}–${losses}`;
}

/** "$12.7M" from an APY in millions (OTC's unit); under a million prints in thousands. */
export function fmtMoney(m: number | null | undefined): string {
  if (m === null || m === undefined || Number.isNaN(m)) return '–';
  return m >= 1 ? `$${m.toFixed(1)}M` : `$${Math.round(m * 1000)}K`;
}

/** A percentile as an ordinal rank band: 0.93 → "93rd". */
export function fmtPctile(x: number | null | undefined): string {
  if (x === null || x === undefined || Number.isNaN(x)) return '–';
  return ordinal(Math.max(1, Math.round(100 * x)));
}

/** "Q2 07:32" from nflverse's seconds remaining in the game; overtime counts its own clock down. */
export function clock(qtr: number | null | undefined, secondsRemaining: number | null | undefined): string {
  if (qtr == null || secondsRemaining == null) return '–';
  const inQuarter = qtr <= 4 ? Math.max(0, secondsRemaining - (4 - qtr) * 900) : secondsRemaining;
  const m = Math.floor(inQuarter / 60);
  const s = inQuarter % 60;
  return `${qtr <= 4 ? `Q${qtr}` : 'OT'} ${m}:${s.toString().padStart(2, '0')}`;
}

/** "OWN 25" / "OPP 18" / "50" from yardline_100 (yards to the opponent's goal line). */
export function yardline(yl100: number | null | undefined): string {
  if (yl100 == null) return '–';
  if (yl100 === 50) return '50';
  return yl100 > 50 ? `OWN ${100 - yl100}` : `OPP ${yl100}`;
}

/** "3rd & 4", "1st & Goal"; special-teams and dead-ball rows (no down) print as an en dash. */
export function downDistance(down: number | null | undefined, ydstogo: number | null | undefined, goalToGo?: number | null): string {
  if (down == null) return '–';
  return `${ordinal(down)} & ${goalToGo ? 'Goal' : (ydstogo ?? '–')}`;
}

/** A rate with one decimal ("72.4%"), the most an in-game sample can carry. */
export function fmtRate1(x: number | null | undefined): string {
  return fmtPct(x, 1);
}

export type StatKind = 'rate' | 'epa' | 'count' | 'number';

/** One value the way its kind reads: a rate to one decimal, EPA to two, a count whole, a number to one decimal. */
export function fmtStat(x: number | null | undefined, kind: StatKind): string {
  if (x === null || x === undefined || Number.isNaN(x)) return '–';
  if (kind === 'rate') return fmtRate1(x);
  if (kind === 'epa') return fmtEpa(x, 2);
  if (kind === 'count') return `${Math.round(x)}`;
  return fmtNum(x, 1);
}

/**
 * The gap to the league in the kind's own unit: "+14.6 pp vs NFL" for a rate, "+0.08 vs NFL" for EPA, "about NFL avg"
 * inside the noise (2 pp, 0.02 EPA, 0.1 otherwise), "" when either side is missing. Never coloured by itself.
 */
export function fmtDelta(value: number | null | undefined, league: number | null | undefined, kind: StatKind): string {
  if (value == null || league == null || Number.isNaN(value) || Number.isNaN(league)) return '';
  const d = value - league;
  const eps = 1e-9; // 2.1 − 2.0 is 0.10000000000000009
  if (kind === 'rate') {
    const pp = 100 * d;
    return Math.abs(pp) <= 2 + eps ? 'about NFL avg' : `${pp > 0 ? '+' : '-'}${Math.abs(pp).toFixed(1)} pp vs NFL`;
  }
  const noise = kind === 'epa' ? 0.02 : 0.1;
  const digits = kind === 'epa' ? 2 : 1;
  return Math.abs(d) <= noise + eps ? 'about NFL avg' : `${d > 0 ? '+' : '-'}${Math.abs(d).toFixed(digits)} vs NFL`;
}

/** "+15 pp" / "-8 pp": a whole-point gap between two rates for running text. */
export function ppGap(value: number, league: number): string {
  const pp = Math.round(100 * (value - league));
  return `${pp > 0 ? '+' : pp < 0 ? '-' : ''}${Math.abs(pp)} pp`;
}

/**
 * nflverse play text without the clock, the formation note and the jersey numbers:
 * "(2:00) (Shotgun) 5-J.Daniels pass incomplete deep right to 13-T.Burks (6-M.Mustapha)." →
 * "J.Daniels pass incomplete deep right to T.Burks (M.Mustapha)."
 */
export function cleanDesc(desc: string | null | undefined): string {
  if (!desc) return '';
  return desc
    .replace(/^\(\d+:\d+\)\s*/, '')
    .replace(/\((Shotgun|No Huddle|No Huddle, Shotgun|Pass formation|Punt formation|Field Goal formation|Run formation)\)\s*/gi, '')
    .replace(/\b\d{1,2}-(?=[A-Z])/g, '')
    .trim();
}
