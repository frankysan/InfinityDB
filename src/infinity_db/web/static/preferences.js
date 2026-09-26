const REMEMBER_SETTINGS_KEY = "infinity-db-remember-settings";
const DISTANCE_UNIT_KEY = "infinity-db-distance-unit";
const DEVELOPER_MODE_KEY = "infinity-db-developer-mode";
const DISABLE_CACHE_KEY = "infinity-db-disable-cache";
const OPTIONAL_UNIT_SETTINGS = [
  { id: "mercs-filter", key: "infinity-db-mercs", defaultChecked: true },
  { id: "specops-filter", key: "infinity-db-specops", defaultChecked: true },
  { id: "teamops-filter", key: "infinity-db-teamops", defaultChecked: true },
  { id: "reinforcement-filter", key: "infinity-db-reinforcement", defaultChecked: true },
];
const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;
const DISTANCE_NUMBER_PATTERN = /[+-]?\d+(?:\.\d+)?/g;

function cookieValue(name) {
  const prefix = `${encodeURIComponent(name)}=`;
  return document.cookie.split("; ").find((cookie) => cookie.startsWith(prefix))?.slice(prefix.length);
}

function isRememberingSettings() {
  return cookieValue(REMEMBER_SETTINGS_KEY) === "true";
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

function savedSetting(name) {
  const session = sessionValue(name);
  if (!isRememberingSettings()) return session;

  const persistent = cookieValue(name);
  if (persistent === undefined) return session;
  setSessionValue(name, persistent);
  return persistent;
}

function saveSetting(name, value) {
  setSessionValue(name, value);
  if (isRememberingSettings()) setCookie(name, value);
}

export function distanceUnit() {
  return document.documentElement.dataset.distanceUnit === "in" ? "in" : "cm";
}

export function formatDistanceExtra(value, { showPositiveSign = true, forcePositiveSign = false } = {}) {
  return String(value).replace(DISTANCE_NUMBER_PATTERN, (number) => {
    const converted = distanceUnit() === "in" ? Number(number) / 2.5 : Number(number);
    const sign = converted >= 0 && (forcePositiveSign || (showPositiveSign && number.startsWith("+")))
      ? "+" : "";
    return `${sign}${converted}${distanceUnit() === "in" ? '"' : " cm"}`;
  });
}

export function formatSkillDistanceExtra(value, parameterSemantics = null) {
  const positiveSign = parameterSemantics?.positive_sign || "preserve";
  return formatDistanceExtra(value, {
    showPositiveSign: positiveSign !== "omit",
    forcePositiveSign: positiveSign === "force",
  });
}

export function initializeDistanceUnitToggle() {
  const toggle = document.getElementById("distance-unit-toggle");
  if (!toggle || toggle.dataset.initialized === "true") return;

  toggle.dataset.initialized = "true";
  const savedUnit = savedSetting(DISTANCE_UNIT_KEY);
  const unit = savedUnit === "cm" ? "cm" : "in";
  document.documentElement.dataset.distanceUnit = unit;
  toggle.checked = unit === "in";

  toggle.addEventListener("change", () => {
    const nextUnit = toggle.checked ? "in" : "cm";
    document.documentElement.dataset.distanceUnit = nextUnit;
    saveSetting(DISTANCE_UNIT_KEY, nextUnit);
    window.dispatchEvent(new CustomEvent("distanceunitchange", { detail: nextUnit }));
  });
}

export function initializeDeveloperModeToggle() {
  const toggle = document.getElementById("developer-mode-toggle");
  if (!toggle || toggle.dataset.initialized === "true") return;

  toggle.dataset.initialized = "true";
  const enabled = savedSetting(DEVELOPER_MODE_KEY) === "true";
  document.documentElement.dataset.developerMode = String(enabled);
  toggle.checked = enabled;

  toggle.addEventListener("change", () => {
    const next = toggle.checked;
    document.documentElement.dataset.developerMode = String(next);
    saveSetting(DEVELOPER_MODE_KEY, String(next));
    if (!next) {
      const cacheToggle = document.getElementById("disable-cache-toggle");
      document.documentElement.dataset.disableCache = "false";
      if (cacheToggle) cacheToggle.checked = false;
      saveSetting(DISABLE_CACHE_KEY, "false");
      window.dispatchEvent(new CustomEvent("cachemodechange", { detail: false }));
    }
    window.dispatchEvent(new CustomEvent("developermodechange", { detail: next }));
  });
}

export function cacheBustedUrl(path) {
  if (document.documentElement.dataset.disableCache !== "true") return path;
  const url = new URL(path, window.location.origin);
  url.searchParams.set("cache_bust", String(Date.now()));
  return `${url.pathname}${url.search}`;
}

export function initializeDisableCacheToggle() {
  const toggle = document.getElementById("disable-cache-toggle");
  if (!toggle || toggle.dataset.initialized === "true") return;

  toggle.dataset.initialized = "true";
  const enabled = document.documentElement.dataset.developerMode === "true"
    && savedSetting(DISABLE_CACHE_KEY) === "true";
  document.documentElement.dataset.disableCache = String(enabled);
  toggle.checked = enabled;
  toggle.addEventListener("change", () => {
    const next = toggle.checked;
    document.documentElement.dataset.disableCache = String(next);
    saveSetting(DISABLE_CACHE_KEY, String(next));
    window.dispatchEvent(new CustomEvent("cachemodechange", { detail: next }));
  });
}

export function initializeOptionalUnitToggles() {
  for (const { id, key, defaultChecked } of OPTIONAL_UNIT_SETTINGS) {
    const toggle = document.getElementById(id);
    if (!toggle || toggle.dataset.initialized === "true") continue;

    toggle.dataset.initialized = "true";
    const saved = savedSetting(key);
    toggle.checked = saved === undefined ? defaultChecked : saved === "true";
    toggle.addEventListener("change", () => {
      saveSetting(key, String(toggle.checked));
      window.dispatchEvent(new CustomEvent("optionalunitschange", { detail: optionalUnitFilters() }));
    });
  }
}

export function optionalUnitFilters() {
  return Object.fromEntries(OPTIONAL_UNIT_SETTINGS.map(({ id, key, defaultChecked }) => [
    key.replace("infinity-db-", ""), document.getElementById(id)?.checked ?? defaultChecked,
  ]));
}

export function initializeRememberSettingsToggle() {
  const toggle = document.getElementById("remember-settings-toggle");
  const dialog = document.getElementById("cookie-consent-dialog");
  if (!toggle || !dialog || toggle.dataset.initialized === "true") return;

  toggle.dataset.initialized = "true";
  toggle.checked = isRememberingSettings();

  toggle.addEventListener("change", () => {
    if (!toggle.checked) {
      removeCookie(REMEMBER_SETTINGS_KEY);
      removeCookie(DISTANCE_UNIT_KEY);
      removeCookie(DEVELOPER_MODE_KEY);
      removeCookie(DISABLE_CACHE_KEY);
      OPTIONAL_UNIT_SETTINGS.forEach(({ key }) => removeCookie(key));
      return;
    }

    dialog.returnValue = "";
    dialog.showModal();
  });

  dialog.addEventListener("close", () => {
    if (dialog.returnValue !== "accept") {
      toggle.checked = false;
      return;
    }

    setCookie(REMEMBER_SETTINGS_KEY, "true");
    setCookie(DISTANCE_UNIT_KEY, document.getElementById("distance-unit-toggle")?.checked ? "in" : "cm");
    setCookie(DEVELOPER_MODE_KEY, String(document.getElementById("developer-mode-toggle")?.checked));
    setCookie(DISABLE_CACHE_KEY, String(document.getElementById("disable-cache-toggle")?.checked));
    OPTIONAL_UNIT_SETTINGS.forEach(({ id, key, defaultChecked }) => {
      setCookie(key, String(document.getElementById(id)?.checked ?? defaultChecked));
    });
  });
}

initializeRememberSettingsToggle();
initializeDeveloperModeToggle();
initializeDisableCacheToggle();
initializeOptionalUnitToggles();
initializeDistanceUnitToggle();
