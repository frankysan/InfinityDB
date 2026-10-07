(() => {
  const REMEMBER_SETTINGS_KEY = "infinity-db-remember-settings";
  const THEME_PREFERENCE_KEY = "infinity-db-theme";
  const THEME_OPTIONS = Object.freeze([
    Object.freeze({ value: "system", label: "System" }),
    Object.freeze({ value: "light", label: "Light" }),
    Object.freeze({ value: "dark", label: "Dark" }),
  ]);
  const THEME_VALUES = new Set(THEME_OPTIONS.map(({ value }) => value));

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

  function savedThemeSelection() {
    const session = sessionValue(THEME_PREFERENCE_KEY);
    if (cookieValue(REMEMBER_SETTINGS_KEY) !== "true") return session;
    return cookieValue(THEME_PREFERENCE_KEY) ?? session;
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
    normalizeSelection,
    applySelection,
  });

  applySelection(savedThemeSelection());
})();
