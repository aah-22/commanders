import { Component, computed, input } from '@angular/core';
import { SeasonSummary } from '../../core/api.service';
import { fmtEpa, fmtNum, fmtSignedPct, ordinal, record } from '../../core/format';
import { StatTile } from '../../shared/stat-tile';

/** Six headline tiles: record, points, offence and defence EPA/play with league rank, PROE, Pythagorean win %. */
@Component({
  selector: 'app-record-strip',
  imports: [StatTile],
  template: `
    <div class="grid strip">
      @for (t of tiles(); track t.label) {
        <app-stat-tile [label]="t.label" [value]="t.value" [delta]="t.delta" />
      }
    </div>
  `,
  styles: `
    .strip { grid-template-columns: repeat(2, 1fr); }
    @media (min-width: 700px) { .strip { grid-template-columns: repeat(3, 1fr); } }
    @media (min-width: 1100px) { .strip { grid-template-columns: repeat(6, 1fr); } }
  `,
})
export class RecordStrip {
  readonly summary = input.required<SeasonSummary>();

  readonly tiles = computed(() => {
    const s = this.summary();
    const st = s.standing;
    const a = s.aggregate;
    const n = s.league_teams;
    const rank = (key: string) => (a?.ranks[key] ? `${ordinal(a.ranks[key])} of ${n}` : 'no rank yet');
    return [
      {
        label: 'Record',
        value: st ? record(st.wins, st.losses, st.ties) : '–',
        delta: st?.div_rank ? `${ordinal(st.div_rank)} ${st.division ?? ''}`.trim() : 'no games played',
      },
      {
        label: 'Points for – against',
        value: st ? `${st.pf} – ${st.pa}` : '–',
        delta: st ? `${st.point_diff > 0 ? '+' : ''}${st.point_diff} differential` : '',
      },
      { label: 'Offence EPA / play', value: fmtEpa(a?.off_epa_per_play), delta: rank('off_epa_per_play') },
      { label: 'Defence EPA / play allowed', value: fmtEpa(a?.def_epa_per_play), delta: rank('def_epa_per_play') },
      { label: 'Pass rate over expected', value: fmtSignedPct(a?.off_proe), delta: 'neutral downs' },
      {
        label: 'Pythagorean win %',
        value: st?.pythag_win_pct != null ? fmtNum(st.pythag_win_pct, 3).replace(/^0/, '') : '–',
        delta: st?.win_pct != null ? `actual ${fmtNum(st.win_pct, 3).replace(/^0/, '')}` : '',
      },
    ];
  });
}
