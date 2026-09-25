import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface Freshness {
  season: number;
  team: string;
  last_ingest: string | null;
  through_week: number | null;
}

/** Thin typed client over the read-only API; nginx proxies /api/ to the FastAPI service, so paths stay relative. */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api';

  freshness(): Observable<Freshness> {
    return this.http.get<Freshness>(`${this.base}/v1/meta/freshness`);
  }
}
