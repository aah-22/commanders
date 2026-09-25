import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'season', pathMatch: 'full' },
  { path: 'season', loadComponent: () => import('./features/season/season-page').then((m) => m.SeasonDashboardPage) },
  { path: 'explorer', loadComponent: () => import('./features/explorer/explorer-page').then((m) => m.DriveExplorerPage) },
  { path: 'explorer/:gameId', loadComponent: () => import('./features/explorer/explorer-page').then((m) => m.DriveExplorerPage) },
  { path: 'gm/acquisitions', loadComponent: () => import('./features/gm/acquisitions-page').then((m) => m.AcquisitionsPage) },
  { path: 'gm/targets', loadComponent: () => import('./features/gm/targets-page').then((m) => m.TargetsPage) },
  { path: 'players/:id', loadComponent: () => import('./features/player/player-page').then((m) => m.PlayerPage) },
  { path: '**', redirectTo: 'season' },
];
