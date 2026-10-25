import { Component, computed, input, ChangeDetectionStrategy } from '@angular/core';
import { GameInsights } from '../../core/api.service';
import { jumpTo } from './sections';
import { SectionId, takeaways } from './takeaways';

const GLOSSARY: [string, string][] = [
  ['EPA', 'Expected points added: how much a play moved the points the offense could expect from its drive. Per play, +0.10 is a strong day, −0.10 a poor one.'],
  ['Success rate', 'The share of plays that kept the offense on schedule (EPA above zero): consistency rather than big plays.'],
  ['Explosive play', 'A pass of 20+ yards or a run of 12+.'],
  ['Dropback', 'Every play the quarterback set up to pass: attempts, sacks and scrambles. A designed run is everything else.'],
  ['Pass rate over expected', 'Dropback rate minus what the down, distance, clock and score usually produce, on neutral downs (win chance 10–90%). Positive means the team chose to throw more than the game script asked.'],
  ['Play action', 'A dropback that began with a run fake.'],
  ['Screen', 'A short throw behind blockers after the rush is let through.'],
  ['RPO', 'Run-pass option: the quarterback reads a defender after the snap and hands off or throws.'],
  ['Motion', 'A player moved before the snap.'],
  ['Under center / shotgun / pistol', 'Where the quarterback took the snap: at the line, five yards back, or four yards back with the back behind him.'],
  ['Box / light box', 'Defenders near the line at the snap; six or fewer is light and invites the run.'],
  ['Blitz', 'Five or more rushers, or a defender rushing from off the line (FTN charting counts the blitzers).'],
  ['Pressure', 'A sack or a quarterback hit (nflverse records hits, not hurries).'],
  ['Win probability', "nflverse's chance of winning before each play; a swing is how much one play moved it."],
  ['NFL avg', 'The league pooled over the season through the last complete week, by the same definition.'],
];

/** The story block: three to five sentences generated from the numbers, each linking to its section, and the glossary. */
@Component({
  selector: 'app-game-story',
  template: `
    <div class="panel">
      <h2>The story</h2>
      <ol class="takes">
        @for (t of takes(); track $index) {
          <li>{{ t.text }} <a [href]="'#' + t.section" (click)="go($event, t.section)" class="see">see</a></li>
        }
      </ol>
      <details>
        <summary class="muted">What these numbers mean</summary>
        <dl>
          @for (g of glossary; track g[0]) {
            <dt>{{ g[0] }}</dt>
            <dd>{{ g[1] }}</dd>
          }
        </dl>
      </details>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: `
    .takes { margin: 0 0 0.75rem; padding-left: 1.2rem; display: grid; gap: 0.5rem; }
    .takes li { line-height: 1.45; }
    .see { font-size: 0.8rem; margin-left: 0.3rem; white-space: nowrap; }
    dl { margin: 0.5rem 0 0; display: grid; grid-template-columns: max-content 1fr; gap: 0.3rem 0.8rem; font-size: 0.85rem; }
    dt { color: var(--heading); font-weight: 600; }
    dd { margin: 0; color: var(--muted); }
    @media (max-width: 640px) { dl { grid-template-columns: 1fr; } dd { margin-bottom: 0.3rem; } }
  `,
})
export class GameStory {
  readonly insights = input.required<GameInsights>();
  readonly takes = computed(() => takeaways(this.insights()));
  readonly glossary = GLOSSARY;

  go(e: Event, id: SectionId): void {
    e.preventDefault();
    jumpTo(id);
  }
}
