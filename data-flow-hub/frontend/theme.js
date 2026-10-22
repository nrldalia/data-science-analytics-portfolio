export function preferredTheme() {
  try {
    const saved = window.localStorage.getItem('dataflow-theme');
    if (saved === 'light' || saved === 'dark') return saved;
  } catch { /* The theme remains usable when browser storage is disabled. */ }
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

export function applyTheme(theme, persist = false) {
  const chosen = theme === 'light' ? 'light' : 'dark';
  document.documentElement.dataset.theme = chosen;
  document.documentElement.style.colorScheme = chosen;
  if (persist) {
    try { window.localStorage.setItem('dataflow-theme', chosen); } catch { /* Keep the current theme without persistence. */ }
  }
  return chosen;
}
