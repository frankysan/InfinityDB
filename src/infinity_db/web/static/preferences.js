const REMEMBER_SETTINGS_KEY = "infinity-db-remember-settings";
const DISTANCE_UNIT_KEY = "infinity-db-distance-unit";
const DEVELOPER_MODE_KEY = "infinity-db-developer-mode";
const DISABLE_CACHE_KEY = "infinity-db-disable-cache";
const FIRETEAMS_INCLUDE_WILDCARDS_KEY = "infinity-db-fireteams-include-wildcards";
const UNIT_ADVANCED_FILTERS_KEY = "infinity-db-unit-advanced-filters";
const OPTIONAL_UNIT_SETTINGS = [
  { name: "mercs", key: "infinity-db-mercs", defaultValue: true },
  { name: "specops", key: "infinity-db-specops", defaultValue: true },
  { name: "teamops", key: "infinity-db-teamops", defaultValue: true },
  { name: "reinforcement", key: "infinity-db-reinforcement", defaultValue: true },
];
const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;
const settingCache = new Map();

function cookieValue(name) {
  const prefix = `${encodeURIComponent(name)}=`;
  return document.cookie.split("; ").find((cookie) => cookie.startsWith(prefix))?.slice(prefix.length);
}

function setCookie(name, value) {
  document.cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value)}; Path=/; Max-Age=${COOKIE_MAX_AGE_SECONDS}; SameSite=Lax`;
}

function removeCookie(name) {
  document.cookie = `${encodeURIComponent(name)}=; Path=/; Max-Age=0; SameSite=Lax`;
}

function sessionValue(name) {
  try {
    return window.sessionStorage.getItem(name) ?? undefined;
  } catch {
    return undefined;
  }
}

function setSessionValue(name, value) {
  try {
    window.sessionStorage.setItem(name, value);
  } catch {
    // Keep settings usable for the current page if session storage is unavailable.
  }
}

export function rememberSettingsEnabled() {
  return cookieValue(REMEMBER_SETTINGS_KEY) === "true";
}

function savedSetting(name) {
  if (settingCache.has(name)) return settingCache.get(name);

  const session = sessionValue(name);
  if (!rememberSettingsEnabled()) {
    settingCache.set(name, session);
    return session;
  }

  const persistent = cookieValue(name);
  const value = persistent === undefined ? session : persistent;
  if (persistent !== undefined) setSessionValue(name, persistent);
  settingCache.set(name, value);
  return value;
}

function saveSetting(name, value) {
  settingCache.set(name, value);
  setSessionValue(name, value);
  if (rememberSettingsEnabled()) setCookie(name, value);
}

function booleanSetting(name, defaultValue) {
  const saved = savedSetting(name);
  return saved === undefined ? defaultValue : saved === "true";
}

function saveBooleanSetting(name, value) {
  saveSetting(name, String(Boolean(value)));
}

export function distanceUnit() {
  return savedSetting(DISTANCE_UNIT_KEY) === "cm" ? "cm" : "in";
}

export function saveDistanceUnit(unit) {
  saveSetting(DISTANCE_UNIT_KEY, unit === "cm" ? "cm" : "in");
}

export function developerModeEnabled() {
  return booleanSetting(DEVELOPER_MODE_KEY, false);
}

export function saveDeveloperModeEnabled(enabled) {
  const next = Boolean(enabled);
  saveBooleanSetting(DEVELOPER_MODE_KEY, next);
  if (!next) saveBooleanSetting(DISABLE_CACHE_KEY, false);
}

export function disableCacheEnabled() {
  return developerModeEnabled() && booleanSetting(DISABLE_CACHE_KEY, false);
}

export function saveDisableCacheEnabled(enabled) {
  saveBooleanSetting(DISABLE_CACHE_KEY, Boolean(enabled) && developerModeEnabled());
}

export function optionalUnitDefaultFilters() {
  return Object.fromEntries(OPTIONAL_UNIT_SETTINGS.map(({ name, defaultValue }) => [
    name, defaultValue,
  ]));
}

export function optionalUnitFilters() {
  return Object.fromEntries(OPTIONAL_UNIT_SETTINGS.map(({ name, key, defaultValue }) => [
    name, booleanSetting(key, defaultValue),
  ]));
}

export function saveOptionalUnitFilter(name, included) {
  const setting = OPTIONAL_UNIT_SETTINGS.find((candidate) => candidate.name === name);
  if (!setting) return;
  saveBooleanSetting(setting.key, included);
}

export function unitAdvancedFiltersOpen() {
  const saved = savedSetting(UNIT_ADVANCED_FILTERS_KEY);
  return saved === undefined ? null : saved === "true";
}

export function saveUnitAdvancedFiltersOpen(open) {
  saveBooleanSetting(UNIT_ADVANCED_FILTERS_KEY, open);
}

export function fireteamsIncludeWildcards() {
  return booleanSetting(FIRETEAMS_INCLUDE_WILDCARDS_KEY, true);
}

export function saveFireteamsIncludeWildcards(included) {
  saveBooleanSetting(FIRETEAMS_INCLUDE_WILDCARDS_KEY, included);
}

function rememberedSettingValues() {
  const values = [
    [DISTANCE_UNIT_KEY, distanceUnit()],
    [DEVELOPER_MODE_KEY, String(developerModeEnabled())],
    [DISABLE_CACHE_KEY, String(disableCacheEnabled())],
    [FIRETEAMS_INCLUDE_WILDCARDS_KEY, String(fireteamsIncludeWildcards())],
  ];
  const optionalFilters = optionalUnitFilters();
  for (const { name, key } of OPTIONAL_UNIT_SETTINGS) {
    values.push([key, String(optionalFilters[name])]);
  }
  const advancedFilters = unitAdvancedFiltersOpen();
  if (advancedFilters !== null) {
    values.push([UNIT_ADVANCED_FILTERS_KEY, String(advancedFilters)]);
  }
  return values;
}

export function rememberCurrentSettings() {
  const values = rememberedSettingValues();
  setCookie(REMEMBER_SETTINGS_KEY, "true");
  for (const [name, value] of values) setCookie(name, value);
}

export function forgetRememberedSettings() {
  removeCookie(REMEMBER_SETTINGS_KEY);
  for (const name of [
    DISTANCE_UNIT_KEY,
    DEVELOPER_MODE_KEY,
    DISABLE_CACHE_KEY,
    FIRETEAMS_INCLUDE_WILDCARDS_KEY,
    UNIT_ADVANCED_FILTERS_KEY,
    ...OPTIONAL_UNIT_SETTINGS.map(({ key }) => key),
  ]) {
    removeCookie(name);
  }
}
