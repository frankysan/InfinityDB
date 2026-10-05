import {
  developerModeEnabled,
  disableCacheEnabled,
  distanceUnit,
  fireteamsIncludeWildcards,
  forgetRememberedSettings,
  optionalUnitFilters,
  rememberCurrentSettings,
  rememberSettingsEnabled,
  saveDeveloperModeEnabled,
  saveDisableCacheEnabled,
  saveDistanceUnit,
  saveFireteamsIncludeWildcards,
  saveOptionalUnitFilter,
  saveUnitAdvancedFiltersOpen,
  saveThemeSelection,
  themeSelection,
} from "./preferences.js";
import { applyThemeSelection, themeOptions } from "./theme.js";

const OPTIONAL_UNIT_CONTROLS = [
  { id: "mercs-filter", name: "mercs" },
  { id: "specops-filter", name: "specops" },
  { id: "teamops-filter", name: "teamops" },
  { id: "reinforcement-filter", name: "reinforcement" },
];

function syncDocumentPreferenceState() {
  document.documentElement.dataset.distanceUnit = distanceUnit();
  document.documentElement.dataset.developerMode = String(developerModeEnabled());
  document.documentElement.dataset.disableCache = String(disableCacheEnabled());
}

function initializeThemeSelector() {
  const selector = document.getElementById("theme-selector");
  if (!selector || selector.dataset.initialized === "true") return;

  selector.dataset.initialized = "true";
  selector.replaceChildren(...themeOptions().map(({ value, label }) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    return option;
  }));
  selector.value = themeSelection();

  selector.addEventListener("change", () => {
    saveThemeSelection(selector.value);
    const state = applyThemeSelection(themeSelection());
    selector.value = state.selection;
    window.dispatchEvent(new CustomEvent("themechange", { detail: state }));
  });

  const colorScheme = window.matchMedia?.("(prefers-color-scheme: dark)");
  colorScheme?.addEventListener("change", () => {
    if (themeSelection() !== "system") return;
    const state = applyThemeSelection("system");
    window.dispatchEvent(new CustomEvent("themechange", { detail: state }));
  });
}

function initializeDistanceUnitToggle() {
  const toggle = document.getElementById("distance-unit-toggle");
  if (!toggle || toggle.dataset.initialized === "true") return;

  toggle.dataset.initialized = "true";
  const unit = distanceUnit();
  document.documentElement.dataset.distanceUnit = unit;
  toggle.checked = unit === "in";

  toggle.addEventListener("change", () => {
    const nextUnit = toggle.checked ? "in" : "cm";
    saveDistanceUnit(nextUnit);
    document.documentElement.dataset.distanceUnit = nextUnit;
    window.dispatchEvent(new CustomEvent("distanceunitchange", { detail: nextUnit }));
  });
}

function initializeDeveloperModeToggle() {
  const toggle = document.getElementById("developer-mode-toggle");
  if (!toggle || toggle.dataset.initialized === "true") return;

  toggle.dataset.initialized = "true";
  const enabled = developerModeEnabled();
  document.documentElement.dataset.developerMode = String(enabled);
  toggle.checked = enabled;

  toggle.addEventListener("change", () => {
    const next = toggle.checked;
    saveDeveloperModeEnabled(next);
    document.documentElement.dataset.developerMode = String(next);
    if (!next) {
      const cacheToggle = document.getElementById("disable-cache-toggle");
      document.documentElement.dataset.disableCache = "false";
      if (cacheToggle) cacheToggle.checked = false;
      window.dispatchEvent(new CustomEvent("cachemodechange", { detail: false }));
    }
    window.dispatchEvent(new CustomEvent("developermodechange", { detail: next }));
  });
}

function initializeDisableCacheToggle() {
  const toggle = document.getElementById("disable-cache-toggle");
  if (!toggle || toggle.dataset.initialized === "true") return;

  toggle.dataset.initialized = "true";
  const enabled = disableCacheEnabled();
  document.documentElement.dataset.disableCache = String(enabled);
  toggle.checked = enabled;
  toggle.addEventListener("change", () => {
    saveDisableCacheEnabled(toggle.checked);
    const next = disableCacheEnabled();
    toggle.checked = next;
    document.documentElement.dataset.disableCache = String(next);
    window.dispatchEvent(new CustomEvent("cachemodechange", { detail: next }));
  });
}

function initializeOptionalUnitToggles() {
  const filters = optionalUnitFilters();
  for (const { id, name } of OPTIONAL_UNIT_CONTROLS) {
    const toggle = document.getElementById(id);
    if (!toggle || toggle.dataset.initialized === "true") continue;

    toggle.dataset.initialized = "true";
    toggle.checked = filters[name];
    toggle.addEventListener("change", () => {
      saveOptionalUnitFilter(name, toggle.checked);
      window.dispatchEvent(new CustomEvent("optionalunitschange", { detail: optionalUnitFilters() }));
    });
  }
}

function initializeFireteamsIncludeWildcardsToggle() {
  const toggle = document.getElementById("fireteams-include-wildcards-toggle");
  if (!toggle || toggle.dataset.initialized === "true") return;

  toggle.dataset.initialized = "true";
  toggle.checked = fireteamsIncludeWildcards();
  toggle.addEventListener("change", () => {
    saveFireteamsIncludeWildcards(toggle.checked);
    window.dispatchEvent(new CustomEvent("fireteamswildcardschange", { detail: toggle.checked }));
  });
}

function initializeRememberSettingsToggle() {
  const toggle = document.getElementById("remember-settings-toggle");
  const dialog = document.getElementById("cookie-consent-dialog");
  if (!toggle || !dialog || toggle.dataset.initialized === "true") return;

  toggle.dataset.initialized = "true";
  toggle.checked = rememberSettingsEnabled();

  toggle.addEventListener("change", () => {
    if (!toggle.checked) {
      forgetRememberedSettings();
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

    const advancedFilters = document.querySelector(".advanced-filters");
    if (advancedFilters) saveUnitAdvancedFiltersOpen(advancedFilters.open);
    rememberCurrentSettings();
  });
}

export function initializeSettings() {
  syncDocumentPreferenceState();
  initializeThemeSelector();
  initializeRememberSettingsToggle();
  initializeDeveloperModeToggle();
  initializeDisableCacheToggle();
  initializeFireteamsIncludeWildcardsToggle();
  initializeOptionalUnitToggles();
  initializeDistanceUnitToggle();
}

initializeSettings();
