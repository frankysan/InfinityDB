(() => {
  const REMEMBER_SETTINGS_KEY = "infinity-db-remember-settings";
  // Preserve the existing stored mode key and values for installed users.
  const THEME_PREFERENCE_KEY = "infinity-db-theme";
  const PALETTE_PREFERENCE_KEY = "infinity-db-theme-palette";
  const THEME_OPTIONS = Object.freeze([
    Object.freeze({ value: "system", label: "Auto" }),
    Object.freeze({ value: "light", label: "Light" }),
    Object.freeze({ value: "dark", label: "Dark" }),
  ]);
  const THEME_VALUES = new Set(THEME_OPTIONS.map(({ value }) => value));
  const PALETTE_OPTIONS = Object.freeze(JSON.parse(
    document.documentElement.dataset.themeOptions || '[{"value":"infinitydb","label":"InfinityDB"}]',
  ).map(Object.freeze));
  const PALETTE_VALUES = new Set(PALETTE_OPTIONS.map(({ value }) => value));

  function cookieValue(name) {
    const prefix = `${encodeURIComponent(name)}=`;
    return document.cookie
      .split("; ")
      .find((cookie) => cookie.startsWith(prefix))
      ?.slice(prefix.length);
  }

  function sessionValue(name) {
    try {
      return window.sessionStorage.getItem(name) ?? undefined;
    } catch {
      return undefined;
    }
  }

  function savedPreference(key) {
    const session = sessionValue(key);
    if (cookieValue(REMEMBER_SETTINGS_KEY) !== "true") return session;
    return cookieValue(key) ?? session;
  }

  function savedThemeSelection() {
    return savedPreference(THEME_PREFERENCE_KEY);
  }

  function normalizePalette(value) {
    return PALETTE_VALUES.has(value) ? value : "infinitydb";
  }

  function applyPalette(value) {
    const palette = normalizePalette(value);
    document.documentElement.dataset.themePalette = palette;
    return palette;
  }

  function normalizeSelection(value) {
    return THEME_VALUES.has(value) ? value : "system";
  }

  function resolveTheme(selection) {
    if (selection !== "system") return selection;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applySelection(value) {
    const selection = normalizeSelection(value);
    const resolved = resolveTheme(selection);
    document.documentElement.dataset.themePreference = selection;
    document.documentElement.dataset.theme = resolved;
    return Object.freeze({ selection, resolved });
  }

  window.infinityThemeBootstrap = Object.freeze({
    preferenceKey: THEME_PREFERENCE_KEY,
    options: THEME_OPTIONS,
    paletteKey: PALETTE_PREFERENCE_KEY,
    paletteOptions: PALETTE_OPTIONS,
    normalizePalette,
    applyPalette,
    normalizeSelection,
    applySelection,
  });

  applyPalette(savedPreference(PALETTE_PREFERENCE_KEY));
  applySelection(savedThemeSelection());
})();
