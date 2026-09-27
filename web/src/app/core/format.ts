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
