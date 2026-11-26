const bootstrap = window.infinityThemeBootstrap;

if (!bootstrap) {
  throw new Error("Theme bootstrap did not initialize before browser modules.");
}

export const THEME_PREFERENCE_KEY = bootstrap.preferenceKey;
export const PALETTE_PREFERENCE_KEY = bootstrap.paletteKey;

export function paletteOptions() {
  return bootstrap.paletteOptions.map(({ value, label }) => ({ value, label }));
}

export function normalizePaletteSelection(value) {
  return bootstrap.normalizePalette(value);
}

export function applyPaletteSelection(value) {
  return bootstrap.applyPalette(value);
}

export function themeOptions() {
  return bootstrap.options.map(({ value, label }) => ({ value, label }));
}

export function normalizeThemeSelection(value) {
  return bootstrap.normalizeSelection(value);
}

export function applyThemeSelection(value) {
  return bootstrap.applySelection(value);
}
