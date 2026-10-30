/**
 * Turns a search term into a PowerDNS search pattern.
 *
 * A term without wildcard is wrapped in `*` for a full-text (contains) search;
 * a term with `*` or `?` is kept as typed, so the user can still anchor it.
 */
export function toSearchPattern(term: string): string {
  const trimmed = term.trim();
  if (!trimmed || /[*?]/.test(trimmed)) return trimmed;
  return `*${trimmed}*`;
}
