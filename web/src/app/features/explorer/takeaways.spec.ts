import { cleanDesc, fmtDelta, fmtStat, ppGap } from '../../core/format';
import { focusWp, takeaways } from './takeaways';
import { INSIGHTS } from './testing/fixtures';

describe('takeaways', () => {
  it('opens with the result and the offenses, then the biggest departures from the league, at most five lines', () => {
    const t = takeaways(INSIGHTS);
    expect(t.length).toBe(5);
    expect(t[0].text).toBe('WAS beat NYG 27–20 at home. Offense -0.01 EPA / play (NFL avg +0.02); NYG +0.21.');
    expect(t[0].section).toBe('matchup');
    const texts = t.map((x) => x.text);
    // second half (swing of 0.34 EPA / play) outranks the alignment (26 pp), the biggest swing (22 + 5) and the pressure
    expect(texts[1]).toBe('Better after halftime: +0.15 EPA / play in the second half after -0.19 in the first.');
    expect(t[1].section).toBe('drives');
    expect(texts[2]).toBe('The biggest swing: Q4 2:00, 4th & 3 at OPP 24, J.Daniels pass incomplete deep right to T.Burks (M.Mustapha); WAS win chance 23% → 1%.');
    expect(texts[3]).toBe('Lined up under center on 13% of snaps (8 of 61), -26 pp vs the league; shotgun 77%, pistol 10%.');
    expect(texts[4]).toBe('Jayden Daniels was pressured on 31% of dropbacks (14 of 45; NFL 23%), sacked 4 times.');
    expect(t[4].section).toBe('defense');
  });

  it('mentions the pass lean with PROE when it is the largest departure', () => {
    const ins = { ...INSIGHTS, teams: [{ ...INSIGHTS.teams[0], quarters: [], splits: [] }, INSIGHTS.teams[1]], impact_plays: [] };
    const texts = takeaways(ins).map((x) => x.text);
    expect(texts).toContain('Threw on 72% of snaps (42 of 58), +15 pp vs the league rate; pass rate over expected +9% on neutral downs.');
    expect(texts).toContain('Converted 3 of 12 third downs (25%; NFL 40%).');
    expect(texts).toContain('Called screens on 3% of passes (1 of 40), -8 pp vs the league.');
  });

  it('skips rates without enough plays and says so for an unplayed game', () => {
    const thin = { ...INSIGHTS, teams: [{ ...INSIGHTS.teams[0], tendencies: INSIGHTS.teams[0].tendencies.map((s) => ({ ...s, n: 4 })), quarters: [], splits: [] }, INSIGHTS.teams[1]], impact_plays: [] };
    const texts = takeaways(thin).map((x) => x.text);
    expect(texts.some((x) => x.startsWith('Threw'))).toBeFalse();
    const unplayed = { ...INSIGHTS, played: false, teams: [{ ...INSIGHTS.teams[0], points: null, efficiency: [] }, INSIGHTS.teams[1]] };
    expect(takeaways(unplayed)).toEqual([{ text: 'WAS vs NYG, not played yet.', section: 'matchup' }]);
  });

  it('reads win probability from the focus side', () => {
    const p = INSIGHTS.impact_plays[1]; // NYG offense, home wp 0.4 → 0.22
    expect(focusWp(p, true)).toEqual({ before: 0.4, after: jasmine.any(Number) });
    expect(focusWp(p, false).before).toBeCloseTo(0.6);
    expect(focusWp(p, false).after).toBeCloseTo(0.78);
  });

  it('formats stats, gaps and play text', () => {
    expect([fmtStat(0.724, 'rate'), fmtStat(-0.012, 'epa'), fmtStat(3, 'count'), fmtStat(7.94, 'number'), fmtStat(null, 'rate')]).toEqual(['72.4%', '-0.01', '3', '7.9', '–']);
    expect([fmtDelta(0.724, 0.574, 'rate'), fmtDelta(0.45, 0.46, 'rate'), fmtDelta(-0.01, 0.02, 'epa'), fmtDelta(2.1, 2.0, 'number'), fmtDelta(null, 1, 'rate')]).toEqual(['+15.0 pp vs NFL', 'about NFL avg', '-0.03 vs NFL', 'about NFL avg', '']);
    expect([ppGap(0.72, 0.57), ppGap(0.13, 0.39), ppGap(0.5, 0.5)]).toEqual(['+15 pp', '-26 pp', '0 pp']);
    expect(cleanDesc('(2:00) (Shotgun) 5-J.Daniels pass incomplete deep right to 13-T.Burks (6-M.Mustapha).')).toBe('J.Daniels pass incomplete deep right to T.Burks (M.Mustapha).');
    expect(cleanDesc('(No Huddle, Shotgun) 13-B.Purdy pass short middle to 85-G.Kittle to WAS 11 for 12 yards.')).toBe('B.Purdy pass short middle to G.Kittle to WAS 11 for 12 yards.');
  });
});
