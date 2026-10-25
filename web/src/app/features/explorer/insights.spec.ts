import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { GameHeader } from './game-header';
import { GameStory } from './game-story';
import { ImpactPlays } from './impact-plays';
import { MatchupCompare } from './matchup-compare';
import { SectionRail } from './section-rail';
import { SituationsTable } from './situations-table';
import { TendencyPanel } from './tendency-panel';
import { GAME, INSIGHTS } from './testing/fixtures';
import { GAMES } from '../season/testing/fixtures';

describe('insight components', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ providers: [provideRouter([])] }).compileComponents();
  });

  it('the story lists the takeaways with section links and the glossary', () => {
    const fixture = TestBed.createComponent(GameStory);
    fixture.componentRef.setInput('insights', INSIGHTS);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelectorAll('ol.takes li').length).toBe(5);
    expect(el.querySelector('ol.takes li a')?.getAttribute('href')).toBe('#matchup');
    expect(el.textContent).toContain('WAS beat NYG 27–20 at home');
    expect(el.querySelectorAll('dt').length).toBeGreaterThan(10);
  });

  it('the matchup mirrors the two offenses with the league tick and prints every value', () => {
    const fixture = TestBed.createComponent(MatchupCompare);
    fixture.componentRef.setInput('focus', INSIGHTS.teams[0]);
    fixture.componentRef.setInput('opp', INSIGHTS.teams[1]);
    fixture.componentRef.setInput('throughWeek', 2);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const rows = fixture.componentInstance.rows();
    expect(rows.length).toBe(11);
    const epa = rows[0];
    expect([epa.key, epa.fw, epa.ow, epa.lw, epa.fNeg, epa.fTone, epa.oTone]).toEqual(['epa_per_play', jasmine.any(Number), 100, jasmine.any(Number), true, 'bad', 'good']);
    expect(epa.fw).toBeCloseTo((100 * 0.01) / 0.21);
    expect(el.querySelectorAll('.row').length).toBe(11);
    expect(el.textContent).toContain('18th of 32');
    expect(el.querySelectorAll('tbody tr').length).toBe(11);
    expect(el.textContent).toContain('-0.01');
    // a tendency is never coloured
    expect(rows.find((r) => r.key === 'pass_rate')?.fTone).toBe('');
  });

  it('the tendency panel renders labelled bar lists, switches team and marks uncharted splits', () => {
    const fixture = TestBed.createComponent(TendencyPanel);
    fixture.componentRef.setInput('teams', INSIGHTS.teams);
    fixture.componentRef.setInput('mode', 'offense');
    fixture.componentRef.setInput('isCharted', false);
    fixture.componentRef.setInput('throughWeek', 2);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain("WAS's offense, 58 pass and run plays");
    const labels = [...el.querySelectorAll('ul.bars li .lab')].map((x) => x.textContent?.trim());
    expect(labels.slice(0, 3)).toEqual(['Under center', 'Shotgun', 'Pistol']);
    expect(el.textContent).toContain('77.0% (47)');
    expect(el.textContent).toContain('Not charted yet');
    expect(el.querySelectorAll('.cell').length).toBe(INSIGHTS.teams[0].tendencies.length);
    expect(el.textContent).toContain('+15.0 pp vs NFL');
    expect(el.querySelector('.cell .d.good, .cell .d.bad')?.textContent).toContain('+8.1 pp vs NFL'); // pressure, better = low → bad
    const buttons = el.querySelectorAll('.seg button');
    (buttons[1] as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(el.textContent).toContain("NYG's offense");
    expect(el.textContent).toContain('55.0%');
  });

  it('the defense panel names whose defense it is', () => {
    const fixture = TestBed.createComponent(TendencyPanel);
    fixture.componentRef.setInput('teams', INSIGHTS.teams);
    fixture.componentRef.setInput('mode', 'defense');
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain("WAS's defense against NYG's offense, 60 pass and run plays");
    expect(el.querySelectorAll('.cell').length).toBe(INSIGHTS.teams[0].defense.length);
    expect(el.textContent).toContain('not charted yet');
  });

  it('the situations table lists both offenses against the league', () => {
    const fixture = TestBed.createComponent(SituationsTable);
    fixture.componentRef.setInput('focus', INSIGHTS.teams[0]);
    fixture.componentRef.setInput('opp', INSIGHTS.teams[1]);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelectorAll('tbody tr').length).toBe(5);
    expect(el.querySelector('tbody tr td:nth-child(2)')?.textContent).toContain('25.0% (12)');
    expect(el.querySelector('tbody tr td:nth-child(2)')?.classList).toContain('bad');
  });

  it('the swings read from the focus side and the players carry their roles', () => {
    const fixture = TestBed.createComponent(ImpactPlays);
    fixture.componentRef.setInput('plays', INSIGHTS.impact_plays);
    fixture.componentRef.setInput('teams', INSIGHTS.teams);
    fixture.componentRef.setInput('focus', 'WAS');
    fixture.componentRef.setInput('home', 'WAS');
    const drives: number[] = [];
    fixture.componentRef.setInput('onDrive', (d: number) => drives.push(d));
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const rows = fixture.componentInstance.rows();
    expect(rows.map((r) => r.swing)).toEqual([-22, -18]);
    expect(el.textContent).toContain('WAS 23% → 1%');
    expect(el.querySelector('.pill')?.classList).toContain('bad');
    expect(el.textContent).toContain('J.Daniels pass incomplete deep right to T.Burks');
    (el.querySelector('button.link') as HTMLButtonElement).click();
    expect(drives).toEqual([9]);
    expect(el.textContent).toContain('42 passes · 4 carries · 310 yds');
    expect(el.textContent).toContain('-12 WP');
  });

  it('the header shows the quarter line score and jumps between games', () => {
    const fixture = TestBed.createComponent(GameHeader);
    fixture.componentRef.setInput('game', GAME);
    fixture.componentRef.setInput('teams', INSIGHTS.teams);
    fixture.componentRef.setInput('games', GAMES.games.filter((g) => g.result));
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const line = fixture.componentInstance.line();
    expect(line?.labels).toEqual(['Q1', 'Q2', 'Q3', 'Q4']);
    expect(line?.rows.map((r) => [r.team, r.points, r.total])).toEqual([
      ['NYG', [13, 7, 0, 0], 20],
      ['WAS', [3, 0, 14, 10], 27],
    ]);
    expect(el.querySelectorAll('table.line tbody tr').length).toBe(2);
    expect(el.querySelectorAll('select option').length).toBe(2);
    expect(el.querySelector('select option')?.textContent).toContain('Week 1 · @ PHI · L 22–24');
  });

  it('the rail lists the sections and marks the one tapped', () => {
    const fixture = TestBed.createComponent(SectionRail);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const links = [...el.querySelectorAll('a')];
    expect(links.map((a) => a.textContent?.trim())).toEqual(['Story', 'Matchup', 'Drives', 'Offense', 'Defense', 'Situations', 'Big plays', 'Plays']);
    links[3].click();
    fixture.detectChanges();
    expect(fixture.componentInstance.active()).toBe('offense');
    expect(links[3].classList).toContain('on');
  });
});
