/**
 * Explicit light/dark theme selection.
 *
 * The class is always set explicitly, never left absent. AppKit's stylesheet
 * carries a `@media (prefers-color-scheme: dark) { :root:not(.light) { ... } }`
 * block that outranks a bare `:root`, so an unclassed document inherits AppKit's
 * dark fallback rather than this app's palette. Writing `light` or `dark` keeps
 * the decision in one place and keeps it observable in the DOM.
 */

export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'nemweb-app-theme';

/** Read the stored preference, falling back to the operating system. */
export function preferredTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') return stored;
  } catch {
    // Private-mode browsers throw on access rather than returning null.
  }
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return 'light';
}

/** Apply a theme to the document and remember it. */
export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  root.classList.remove('light', 'dark');
  root.classList.add(theme);
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // A failed write only costs persistence, so the theme still applies.
  }
}
