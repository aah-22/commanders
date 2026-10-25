import { SectionId } from './takeaways';

/** The page's sections in order: the rail's chips and every takeaway's "see" link point at these ids. */
export const SECTIONS: { id: SectionId; label: string }[] = [
  { id: 'story', label: 'Story' },
  { id: 'matchup', label: 'Matchup' },
  { id: 'drives', label: 'Drives' },
  { id: 'offense', label: 'Offense' },
  { id: 'defense', label: 'Defense' },
  { id: 'situations', label: 'Situations' },
  { id: 'big-plays', label: 'Big plays' },
  { id: 'plays', label: 'Plays' },
];

/** Scroll a section under the sticky rail; instant when the viewer prefers reduced motion. */
export function jumpTo(id: SectionId): void {
  const el = typeof document === 'undefined' ? null : document.getElementById(id);
  if (!el) return;
  const reduced = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  el.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
}
