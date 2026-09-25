import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { FreshnessBanner } from './shared/freshness-banner';

/** The caabi.dev chrome (shield logo, site links top-right, burgundy active underline) plus this site's own pages. */
@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, FreshnessBanner],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  /** Same list and order as lineup/ui.py LINKS on fantasy.caabi.dev; this site is the active one. */
  readonly siteLinks = [
    { label: 'Anchor', url: 'https://anchor.caabi.dev' },
    { label: 'Fantasy', url: 'https://fantasy.caabi.dev' },
    { label: 'Commanders', url: 'https://commanders.caabi.dev', active: true },
    { label: 'MLflow', url: 'https://mlflow.caabi.dev' },
    { label: 'GitHub', url: 'https://github.com/aah-22' },
  ];
  readonly pages = [
    { path: '/season', label: 'Season' },
    { path: '/explorer', label: 'Drives & plays' },
    { path: '/gm/acquisitions', label: 'Acquisitions' },
    { path: '/gm/targets', label: 'Targets' },
  ];
}
