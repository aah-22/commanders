import { Component, input } from '@angular/core';

/** A–F on the production-minus-expected gap; a dash while the player has not qualified. */
@Component({
  selector: 'app-grade-chip',
  template: `<span class="chip" [class]="'chip g-' + (grade() ?? 'none')" [title]="title()">{{ grade() ?? '–' }}</span>`,
  styles: `
    .chip { display: inline-block; min-width: 1.8rem; text-align: center; padding: 0 0.4rem; border-radius: 6px; border: 1px solid var(--line-2); font-weight: 700; color: var(--muted); }
    .g-A { color: #0a0a0a; background: var(--gold); border-color: var(--gold); }
    .g-B { color: var(--gold); border-color: var(--gold); }
    .g-C { color: var(--text); }
    .g-D { color: #d9534f; border-color: #d9534f; }
    .g-F { color: #0a0a0a; background: var(--burgundy); border-color: var(--burgundy); }
  `,
})
export class GradeChip {
  readonly grade = input<string | null>(null);
  readonly title = input<string>('');
}
