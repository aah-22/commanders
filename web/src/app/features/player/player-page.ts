import { Component, ChangeDetectionStrategy } from '@angular/core';

@Component({
  selector: 'app-player-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h1>Player</h1>
    <p>Game log, percentiles at the position, contract and age curve.</p>
    <div class="panel"><em>Coming in the next phase.</em></div>
  `,
})
export class PlayerPage {}
