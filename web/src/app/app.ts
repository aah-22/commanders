import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { FreshnessBanner } from './shared/freshness-banner';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, FreshnessBanner],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  readonly links = [
    { path: '/season', label: 'Season' },
    { path: '/explorer', label: 'Drives & plays' },
    { path: '/gm/acquisitions', label: 'Acquisitions' },
    { path: '/gm/targets', label: 'Targets' },
  ];
}
