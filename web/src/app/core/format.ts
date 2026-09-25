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
