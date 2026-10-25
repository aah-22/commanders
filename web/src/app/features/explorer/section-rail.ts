import { afterNextRender, Component, DestroyRef, inject, input, signal } from '@angular/core';
import { jumpTo, SECTIONS } from './sections';
import { SectionId } from './takeaways';

/** A sticky row of section chips; the active chip follows the scroll position and a tap scrolls to the section. */
@Component({
  selector: 'app-section-rail',
  template: `
    <nav class="rail" aria-label="Sections of this page">
      @for (s of sections(); track s.id) {
        <a [href]="'#' + s.id" [class.on]="active() === s.id" [attr.aria-current]="active() === s.id ? 'location' : null" (click)="go($event, s.id)">{{ s.label }}</a>
      }
    </nav>
  `,
  styles: `
    .rail { position: sticky; top: 0; z-index: 5; display: flex; gap: 0.4rem; overflow-x: auto; scrollbar-width: none; padding: 0.5rem 0; background: var(--bg); border-bottom: 1px solid var(--line); }
    .rail::-webkit-scrollbar { display: none; }
    a { flex: 0 0 auto; display: inline-flex; align-items: center; min-height: 44px; padding: 0 0.85rem; border: 1px solid var(--line-2); border-radius: 999px; color: var(--muted); font-size: 0.85rem; white-space: nowrap; }
    a.on { color: var(--gold); border-color: var(--gold); }
    a:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
  `,
})
export class SectionRail {
  readonly sections = input(SECTIONS);
  readonly active = signal<SectionId | null>(null);
  private observer?: IntersectionObserver;

  constructor() {
    const destroy = inject(DestroyRef);
    afterNextRender(() => this.watch());
    destroy.onDestroy(() => this.observer?.disconnect());
  }

  /** Scroll-spy: the first observed section whose top has passed the rail becomes the active one. */
  private watch(): void {
    if (typeof IntersectionObserver === 'undefined' || typeof document === 'undefined') return;
    const ids = this.sections().map((s) => s.id);
    const visible = new Set<SectionId>();
    this.observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          const id = e.target.id as SectionId;
          if (e.isIntersecting) visible.add(id);
          else visible.delete(id);
        }
        const first = ids.find((id) => visible.has(id));
        if (first) this.active.set(first);
      },
      { rootMargin: '-56px 0px -55% 0px', threshold: 0 },
    );
    for (const id of ids) {
      const el = document.getElementById(id);
      if (el) this.observer.observe(el);
    }
  }

  go(e: Event, id: SectionId): void {
    e.preventDefault();
    this.active.set(id);
    jumpTo(id);
  }
}
