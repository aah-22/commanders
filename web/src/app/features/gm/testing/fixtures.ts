import { AcquisitionCard, Acquisitions, Models, Need, Target, Targets } from '../../../core/api.service';

function card(p: Partial<AcquisitionCard> & { gsis_id: string; name: string; how: string; pos_group: string }): AcquisitionCard {
  return {
    position: p.pos_group,
    date: '2026-03-15',
    from_team: null,
    draft_round: null,
    draft_pick: null,
    arrival_season: 2026,
    current_team: 'WAS',
    apy: 10,
    contract_years: 3,
    guaranteed: 20,
    year_signed: 2026,
    years_left: 2,
    age: 27,
    games: 3,
    snaps: 180,
    snap_share: 0.9,
    metric: 'epa_per_target',
    production: 0.4,
    production_pct: 0.8,
    qualified: true,
    cost_pct: 0.5,
    graded_seasons: [2026],
    tenure_pct: 0.8,
    expected_pct: 0.55,
    basis: 'model',
    value_gap: 0.25,
    grade: 'A',
    run_id: 'run-value-1',
    model_version: '2',
    ...p,
  };
}

export const ACQUISITIONS: Acquisitions = {
  season: 2026,
  team: 'WAS',
  since: 2025,
  cards: [
    card({ gsis_id: '00-E1', name: 'Odafe Oweh', how: 'free agent', pos_group: 'ED', position: 'ED', apy: 12.65, metric: 'pressure_rate', production: 0.1, production_pct: 1.0, tenure_pct: 1.0, expected_pct: 0.62, value_gap: 0.38, grade: 'A' }),
    card({ gsis_id: '00-W3', name: 'Antonio Williams', how: 'draft', pos_group: 'WR', draft_round: 3, draft_pick: 71, date: '2026-04-30', apy: 1.81, contract_years: 4, qualified: false, production_pct: null, tenure_pct: null, graded_seasons: [], expected_pct: 0.2, value_gap: null, grade: null }),
    card({ gsis_id: '00-W2', name: 'Deebo Samuel', how: 'trade', pos_group: 'WR', from_team: 'SF', arrival_season: 2025, date: '2025-03-01', apy: 17.5, contract_years: 1, years_left: 0, age: 30.6, production_pct: 0.375, tenure_pct: 0.375, graded_seasons: [2025, 2026], expected_pct: 0.6, value_gap: -0.225, grade: 'F', basis: 'cost', run_id: null, model_version: null }),
  ],
};

export const NEED: Need = {
  season: 2026,
  team: 'WAS',
  groups: [
    {
      pos_group: 'LB',
      starters: 1,
      starter_pct: 1,
      starters_expiring: 1,
      starters_aging: 1,
      avg_age: 36.2,
      contract_years_left: 0,
      depth: 1,
      need_score: 50,
      need_rank: 1,
      starter_list: [{ gsis_id: '00-L1', name: 'Bobby Wagner', position: 'LB', age: 36.2, snap_share: 1, production_pct: 1, years_left: 0, apy: 9.5 }],
    },
    {
      pos_group: 'WR',
      starters: 3,
      starter_pct: 0.5625,
      starters_expiring: 1,
      starters_aging: 2,
      avg_age: 28.3,
      contract_years_left: 1,
      depth: 3,
      need_score: 46.9,
      need_rank: 2,
      starter_list: [
        { gsis_id: '00-W1', name: 'Terry McLaurin', position: 'WR', age: 31, snap_share: 0.95, production_pct: 0.75, years_left: 1, apy: 32.3 },
        { gsis_id: '00-W2', name: 'Deebo Samuel', position: 'WR', age: 30.6, snap_share: 0.9, production_pct: 0.375, years_left: 0, apy: 17.5 },
        { gsis_id: '00-W3', name: 'Antonio Williams', position: 'WR', age: 23.3, snap_share: 0.4, production_pct: null, years_left: 3, apy: 1.81 },
      ],
    },
    {
      pos_group: 'QB',
      starters: 1,
      starter_pct: 1,
      starters_expiring: 0,
      starters_aging: 0,
      avg_age: 25.7,
      contract_years_left: 1,
      depth: 1,
      need_score: 0,
      need_rank: 3,
      starter_list: [{ gsis_id: '00-Q1', name: 'Jayden Daniels', position: 'QB', age: 25.7, snap_share: 1, production_pct: 1, years_left: 1, apy: 9.4 }],
    },
  ],
};

function target(p: Partial<Target> & { gsis_id: string; name: string; team: string; pos_group: string; score: number }): Target {
  return {
    position: p.pos_group,
    age: 26,
    games: 3,
    production_pct: 0.8,
    projected_pct: 0.75,
    projection_run_id: 'run-next-1',
    apy: 20,
    years_left: 0,
    reason: 'pending free agent',
    need_score: 46.9,
    run_id: 'run-score-1',
    version: 'formula-1',
    ...p,
  };
}

export const TARGETS: Targets = {
  season: 2026,
  team: 'WAS',
  position: null,
  live: false,
  scored_at: '2026-09-27 10:30:00+00:00',
  targets: [
    target({ gsis_id: '00-W4', name: 'A.J. Brown', team: 'PHI', pos_group: 'WR', score: 0.469, production_pct: 1, apy: 32 }),
    target({ gsis_id: '00-W5', name: 'Malik Nabers', team: 'NYG', pos_group: 'WR', score: 0.176, production_pct: 0.375, projected_pct: 0.4, reason: 'pending free agent, losing team', years_left: 0, apy: 7.3 }),
    target({ gsis_id: '00-L2', name: 'Some Backer', team: 'NYG', pos_group: 'LB', score: 0.3, production_pct: 0.6, reason: 'pending free agent, losing team', need_score: 50 }),
  ],
};

export const MODELS: Models = {
  experiment: 'commanders',
  tracking: 'https://mlflow.caabi.dev',
  outputs: [
    { model: 'production-next', season: 2026, version: '3', run_id: 'run-next-1', rows: 812, scored_at: '2026-09-27 10:30:00+00:00' },
    { model: 'acquisition-value', season: 2026, version: '2', run_id: 'run-value-1', rows: 640, scored_at: '2026-09-27 10:30:00+00:00' },
    { model: 'target-rank', season: 2026, version: 'formula-1', run_id: 'run-score-1', rows: 120, scored_at: '2026-09-27 10:30:00+00:00' },
  ],
  jobs: [
    { kind: 'ingest', status: 'ok', season: 2026, finished_at: '2026-09-27 09:40:00+00:00', detail: {} },
    { kind: 'score', status: 'ok', season: 2026, finished_at: '2026-09-27 10:30:00+00:00', detail: { 'production-next': 812 } },
  ],
};
