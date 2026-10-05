import { getArmies, getCatalogItems, getUnitFilters, getUnits } from "./api.js";
import {
  optionalUnitDefaultFilters, optionalUnitFilters, saveUnitAdvancedFiltersOpen,
  unitAdvancedFiltersOpen,
} from "./preferences.js";
import { renderUnitRows } from "./unit-list.js";
import { readShareState, writeShareState } from "./share-state.js";

const PAGE_SIZE = 50;
const number = new Intl.NumberFormat();
const byId = (id) => document.getElementById(id);
const elements = {
  filters: byId("filters"), army: byId("army-filter"), search: byId("unit-search"),
  skill: byId("skill-filter"), equipment: byId("equipment-filter"), weapon: byId("weapon-filter"),
  troopType: byId("troop-type-filter"), classification: byId("classification-filter"),
  characteristic: byId("characteristic-filter"),
  ava: byId("ava-filter"), avaMin: byId("ava-min-filter"), avaMax: byId("ava-max-filter"),
  avaMinValue: byId("ava-min-value"), avaMaxValue: byId("ava-max-value"),
  points: byId("points-filter"), pointsMin: byId("points-min-filter"), pointsMax: byId("points-max-filter"),
  pointsMinValue: byId("points-min-value"), pointsMaxValue: byId("points-max-value"),
  swc: byId("swc-filter"), swcMin: byId("swc-min-filter"), swcMax: byId("swc-max-filter"),
  swcMinValue: byId("swc-min-value"), swcMaxValue: byId("swc-max-value"),
  optionalUnitContext: byId("optional-unit-context"), extended: byId("extended-results"),
  clear: byId("clear-filters"), unitCount: byId("unit-count"), armyCount: byId("army-count"),
  declaredMembership: byId("declared-membership-context"),
  unitCountShown: byId("unit-count-shown-breakdown"),
  unitCountFiltered: byId("unit-count-filtered-breakdown"),
  unitCountFilteredTotal: byId("unit-count-filtered-total"),
  summary: byId("results-summary"), results: byId("results"), loading: byId("loading-state"),
  error: byId("error-state"), errorMessage: byId("error-message"), empty: byId("empty-state"),
  emptyTitle: byId("empty-title"), emptyMessage: byId("empty-message"), emptyClear: byId("empty-clear"),
  table: byId("table-container"), list: byId("unit-list"),
  pagination: [byId("pagination-top"), byId("pagination-bottom")],
  pageSummary: [byId("page-summary-top"), byId("page-summary-bottom")],
  previous: [byId("previous-page-top"), byId("previous-page-bottom")],
  next: [byId("next-page-top"), byId("next-page-bottom")],
  sort: document.querySelector("#table-container th"),
};

const numericRangeControls = {
  ava: {
    exact: elements.ava, minimum: elements.avaMin, maximum: elements.avaMax,
    minimumValue: elements.avaMinValue, maximumValue: elements.avaMaxValue,
    reset: byId("ava-range-reset"),
    container: document.querySelector('[data-range-filter="ava"]'),
    minimumState: "avaMin", maximumState: "avaMax", metadata: null,
  },
  points: {
    exact: elements.points, minimum: elements.pointsMin, maximum: elements.pointsMax,
    minimumValue: elements.pointsMinValue, maximumValue: elements.pointsMaxValue,
    reset: byId("points-range-reset"),
    container: document.querySelector('[data-range-filter="points"]'),
    minimumState: "pointsMin", maximumState: "pointsMax", metadata: null,
  },
  swc: {
    exact: elements.swc, minimum: elements.swcMin, maximum: elements.swcMax,
    minimumValue: elements.swcMinValue, maximumValue: elements.swcMaxValue,
    reset: byId("swc-range-reset"),
    container: document.querySelector('[data-range-filter="swc"]'),
    minimumState: "swcMin", maximumState: "swcMax", metadata: null,
  },
};

document.querySelector(".results-toolbar").remove();
elements.sortButton = document.createElement("button");
elements.sortButton.className = "unit-sort-button";
elements.sortButton.type = "button";
elements.sort.classList.add("sortable-unit-name");
elements.sort.replaceChildren(elements.sortButton);

const OPTIONAL_UNIT_KEYS = ["mercs", "specops", "teamops", "reinforcement"];
const OPTIONAL_UNIT_LABELS = {
  mercs: "Mercenaries",
  specops: "Spec-Ops",
  teamops: "Team Operations",
  reinforcement: "Reinforcements",
};

let state = readLocation();
const advancedFilters = document.querySelector(".advanced-filters");
if (advancedFilters) {
  const savedAdvancedFiltersOpen = unitAdvancedFiltersOpen();
  const hasAdvancedFilterState = state.skillId || state.equipmentId || state.weaponId
    || state.troopType || state.classification || state.characteristic
    || state.ava || state.avaMin || state.avaMax
    || state.points || state.pointsMin || state.pointsMax
    || state.swc || state.swcMin || state.swcMax;
  advancedFilters.open = savedAdvancedFiltersOpen ?? Boolean(hasAdvancedFilterState);
  advancedFilters.addEventListener("toggle", () => {
    saveUnitAdvancedFiltersOpen(advancedFilters.open);
  });
}
let armiesLoaded = false;
let requestNumber = 0;
let controller;
let searchTimer;

function readOptionalUnitLocation(params) {
  const hasExplicitState = OPTIONAL_UNIT_KEYS.some((key) => params.has(key));
  if (!hasExplicitState) {
    return { filters: optionalUnitFilters(), source: "preferences", invalid: false };
  }

  const defaults = optionalUnitDefaultFilters();
  let invalid = false;
  const filters = Object.fromEntries(OPTIONAL_UNIT_KEYS.map((key) => {
    const value = params.get(key);
    if (value === null) return [key, defaults[key]];
    if (value === "0" || value === "1") return [key, value === "1"];
    invalid = true;
    return [key, defaults[key]];
  }));
  return { filters, source: "url", invalid };
}

function optionalUnitPreferenceDifferences() {
  const preferences = optionalUnitFilters();
  return OPTIONAL_UNIT_KEYS
    .filter((key) => state[key] !== preferences[key])
    .map((key) => `${OPTIONAL_UNIT_LABELS[key]} ${state[key] ? "included" : "excluded"}`);
}

function renderOptionalUnitContext() {
  const context = elements.optionalUnitContext;
  if (!context) return;
  const differences = optionalUnitPreferenceDifferences();
  const correction = state.optionalUnitInvalid
    ? "Unsupported optional-unit URL values were reset to defaults. "
    : "";
  context.textContent = differences.length
    ? `${correction}View differs from Settings: ${differences.join("; ")}.`
    : `${correction}View matches optional-unit Settings.`;
}

function hasActiveFilters() {
  return state.armyId || state.declaredFactionId || state.search
    || state.skillId || state.equipmentId || state.weaponId
    || state.troopType || state.classification || state.characteristic
    || state.ava || state.avaMin || state.avaMax
    || state.points || state.pointsMin || state.pointsMax
    || state.swc || state.swcMin || state.swcMax
    || optionalUnitPreferenceDifferences().length > 0;
}

function domainFilterIdentifier(value) {
  return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value) ? value : "";
}

function integerFilterValue(value, { max = Number.MAX_SAFE_INTEGER } = {}) {
  if (!/^\d+$/.test(value)) return "";
  const numeric = Number(value);
  return Number.isSafeInteger(numeric) && numeric <= max ? String(numeric) : "";
}

function decimalFilterValue(value) {
  if (!/^\d+(?:\.\d+)?$/.test(value)) return "";
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric >= 0 ? value : "";
}

function avaExactFilterValue(value) {
  const normalized = value.trim().toLowerCase();
  if (normalized === "t" || normalized === "total") return "total";
  return integerFilterValue(normalized, { max: 99 });
}

function swcExactFilterValue(value) {
  const normalized = value.trim();
  return /^(?:\+)?(?:0|[1-9]\d*)(?:\.\d+)?$/.test(normalized) || normalized === "-"
    ? normalized : "";
}

function exactNumericLabel(name, value) {
  if (name === "ava" && value === "total") return "Total";
  return value;
}

function populateNumericFilter(name, metadata) {
  const control = numericRangeControls[name];
  if (!control) return;
  control.exact.replaceChildren(new Option("Any", ""));
  const values = Array.isArray(metadata?.exact_values) ? metadata.exact_values : [];
  for (const value of values) {
    control.exact.add(new Option(exactNumericLabel(name, value), value));
  }
  const currentExact = state[name];
  if (currentExact && !values.includes(currentExact)) {
    control.exact.add(new Option(`${exactNumericLabel(name, currentExact)} (not present)`, currentExact));
  }
  control.exact.disabled = false;

  const range = metadata?.range;
  if (!range || !Number.isFinite(Number(range.min)) || !Number.isFinite(Number(range.max))) {
    control.metadata = null;
    control.minimum.disabled = true;
    control.maximum.disabled = true;
    control.minimumValue.textContent = "—";
    control.maximumValue.textContent = "—";
    control.container.classList.remove("is-active");
    control.reset.disabled = true;
    return;
  }
  control.metadata = {
    min: Number(range.min),
    max: Number(range.max),
    step: Number(range.step) || 1,
  };
  for (const input of [control.minimum, control.maximum]) {
    input.min = String(control.metadata.min);
    input.max = String(control.metadata.max);
    input.step = String(control.metadata.step);
    input.disabled = false;
  }
}

function rangeDisplayValue(value) {
  return String(Number(value));
}

function updateNumericRangeVisuals(control) {
  if (!control.metadata) return;
  const minimum = Number(control.minimum.value);
  const maximum = Number(control.maximum.value);
  const span = control.metadata.max - control.metadata.min;
  const start = span ? ((minimum - control.metadata.min) / span) * 100 : 0;
  const end = span ? ((maximum - control.metadata.min) / span) * 100 : 100;
  control.container.style.setProperty("--range-start", `${Math.max(0, Math.min(100, start))}%`);
  control.container.style.setProperty("--range-end", `${Math.max(0, Math.min(100, end))}%`);
  control.minimumValue.textContent = rangeDisplayValue(minimum);
  control.maximumValue.textContent = rangeDisplayValue(maximum);
  const isActive = minimum !== control.metadata.min || maximum !== control.metadata.max;
  control.container.classList.toggle("is-active", isActive);
  control.reset.disabled = !isActive;
}

function syncNumericRangeControl(control) {
  if (!control.metadata) return;
  const requestedMinimum = state[control.minimumState];
  const requestedMaximum = state[control.maximumState];
  const minimum = requestedMinimum === ""
    ? control.metadata.min : Number(requestedMinimum);
  const maximum = requestedMaximum === ""
    ? control.metadata.max : Number(requestedMaximum);
  control.minimum.value = String(Math.max(control.metadata.min, Math.min(control.metadata.max, minimum)));
  control.maximum.value = String(Math.max(control.metadata.min, Math.min(control.metadata.max, maximum)));
  updateNumericRangeVisuals(control);
}

function resetNumericRangeControl(control) {
  if (!control.metadata) return;
  control.minimum.value = String(control.metadata.min);
  control.maximum.value = String(control.metadata.max);
  updateNumericRangeVisuals(control);
}

function numericRangeStateValue(name, control, input, boundary) {
  if (!control.metadata) return "";
  const numeric = Number(input.value);
  if (numeric === boundary) return "";
  const value = String(numeric);
  return name === "swc" ? decimalFilterValue(value) : integerFilterValue(value, { max: name === "ava" ? 99 : Number.MAX_SAFE_INTEGER });
}

function activateNumericRangeThumb(control, input) {
  control.minimum.style.zIndex = input === control.minimum ? "5" : "3";
  control.maximum.style.zIndex = input === control.maximum ? "5" : "4";
}

function updateNumericRangeFromInput(control, changed) {
  let minimum = Number(control.minimum.value);
  let maximum = Number(control.maximum.value);
  if (minimum > maximum) {
    if (changed === control.minimum) {
      control.maximum.value = control.minimum.value;
      maximum = minimum;
    } else {
      control.minimum.value = control.maximum.value;
      minimum = maximum;
    }
  }
  if (minimum <= maximum) control.exact.value = "";
  activateNumericRangeThumb(control, changed);
  updateNumericRangeVisuals(control);
}

function readLocation() {
  const { params } = readShareState("units");
  const optionalUnits = readOptionalUnitLocation(params);
  const offset = Number(params.get("offset") || 0);
  const armyId = params.get("army_id") || "";
  const declaredFactionId = params.get("declared_faction_id") || "";
  const skillId = params.get("skill_id") || "";
  const equipmentId = params.get("equipment_id") || "";
  const weaponId = params.get("weapon_id") || "";
  const troopType = params.get("troop_type") || "";
  const classification = params.get("classification") || "";
  const characteristic = params.get("characteristic") || "";
  const ava = params.get("ava") || "";
  const avaMin = params.get("ava_min") || "";
  const avaMax = params.get("ava_max") || "";
  const points = params.get("points") || "";
  const pointsMin = params.get("points_min") || "";
  const pointsMax = params.get("points_max") || "";
  const swc = swcExactFilterValue(params.get("swc") || "");
  const swcMin = decimalFilterValue(params.get("swc_min") || "");
  const swcMax = decimalFilterValue(params.get("swc_max") || "");
  const avaExact = avaExactFilterValue(ava);
  const pointsExact = integerFilterValue(points);
  const swcExact = swc;
  return {
    armyId: domainFilterIdentifier(armyId),
    declaredFactionId: /^\d+$/.test(declaredFactionId) ? declaredFactionId : "",
    skillId: domainFilterIdentifier(skillId),
    equipmentId: domainFilterIdentifier(equipmentId),
    weaponId: domainFilterIdentifier(weaponId),
    troopType: domainFilterIdentifier(troopType),
    classification: domainFilterIdentifier(classification),
    characteristic: domainFilterIdentifier(characteristic),
    ava: avaExact,
    avaMin: avaExact ? "" : integerFilterValue(avaMin, { max: 99 }),
    avaMax: avaExact ? "" : integerFilterValue(avaMax, { max: 99 }),
    points: pointsExact,
    pointsMin: pointsExact ? "" : integerFilterValue(pointsMin),
    pointsMax: pointsExact ? "" : integerFilterValue(pointsMax),
    swc: swcExact,
    swcMin: swcExact ? "" : swcMin,
    swcMax: swcExact ? "" : swcMax,
    search: (params.get("search") || "").trim().slice(0, 200),
    ...optionalUnits.filters,
    optionalUnitSource: optionalUnits.source,
    optionalUnitInvalid: optionalUnits.invalid,
    descending: params.get("order") === "desc",
    extended: params.get("extended") === "1",
    offset: Number.isSafeInteger(offset) && offset >= 0 ? Math.floor(offset / PAGE_SIZE) * PAGE_SIZE : 0,
    limit: PAGE_SIZE,
  };
}

function writeLocation(replace = false) {
  const params = new URLSearchParams();
  if (state.armyId) params.set("army_id", state.armyId);
  if (state.declaredFactionId) params.set("declared_faction_id", state.declaredFactionId);
  if (state.search) params.set("search", state.search);
  if (state.skillId) params.set("skill_id", state.skillId);
  if (state.equipmentId) params.set("equipment_id", state.equipmentId);
  if (state.weaponId) params.set("weapon_id", state.weaponId);
  if (state.troopType) params.set("troop_type", state.troopType);
  if (state.classification) params.set("classification", state.classification);
  if (state.characteristic) params.set("characteristic", state.characteristic);
  if (state.ava) params.set("ava", state.ava);
  if (state.avaMin) params.set("ava_min", state.avaMin);
  if (state.avaMax) params.set("ava_max", state.avaMax);
  if (state.points) params.set("points", state.points);
  if (state.pointsMin) params.set("points_min", state.pointsMin);
  if (state.pointsMax) params.set("points_max", state.pointsMax);
  if (state.swc) params.set("swc", state.swc);
  if (state.swcMin) params.set("swc_min", state.swcMin);
  if (state.swcMax) params.set("swc_max", state.swcMax);
  if (state.offset) params.set("offset", String(state.offset));
  for (const key of OPTIONAL_UNIT_KEYS) params.set(key, state[key] ? "1" : "0");
  if (state.descending) params.set("order", "desc");
  if (state.extended) params.set("extended", "1");
  writeShareState("units", params, { replace });
}

function syncFilters() {
  elements.army.value = state.armyId;
  elements.search.value = state.search;
  elements.skill.value = state.skillId;
  elements.equipment.value = state.equipmentId;
  elements.weapon.value = state.weaponId;
  elements.troopType.value = state.troopType;
  elements.classification.value = state.classification;
  elements.characteristic.value = state.characteristic;
  elements.extended.checked = state.extended;
  elements.ava.value = state.ava;
  elements.points.value = state.points;
  elements.swc.value = state.swc;
  for (const control of Object.values(numericRangeControls)) syncNumericRangeControl(control);
  elements.clear.disabled = !hasActiveFilters();
  updateSortButton();
}

function updateSortButton() {
  const order = state.descending ? "Z–A ↓" : "A–Z ↑";
  elements.sortButton.textContent = `Unit name ${order}`;
  elements.sortButton.setAttribute(
    "aria-label",
    `Unit name, ${state.descending ? "reverse alphabetical" : "alphabetical"} order. Activate to reverse the order.`,
  );
  elements.sort.setAttribute("aria-sort", state.descending ? "descending" : "ascending");
}

function showPanel(panel) {
  for (const element of [elements.loading, elements.error, elements.empty, elements.table]) {
    element.hidden = element !== panel;
  }
  const loading = panel === elements.loading;
  elements.results.setAttribute("aria-busy", String(loading));
  if (panel !== elements.table) elements.pagination.forEach((pagination) => { pagination.hidden = true; });
}

function armyFilterValue(army) {
  return army.public_slug || String(army.id);
}

function normalizeArmyFilterState(armies) {
  const current = state.armyId;
  if (!current) return false;
  const army = armies.find(
    (candidate) => armyFilterValue(candidate) === current || String(candidate.id) === current,
  );
  if (!army) {
    state.armyId = "";
    state.offset = 0;
    return true;
  }
  const replacement = armyFilterValue(army);
  if (replacement === current) return false;
  state.armyId = replacement;
  return true;
}

function populateArmies(armies) {
  // Keep source strings out of HTML so upstream data is always treated as text.
  elements.army.replaceChildren(new Option("All armies", ""));
  const playableArmies = armies.filter((army) => army.playable !== false);
  const normalizedArmyFilter = normalizeArmyFilterState(playableArmies);
  const shownGroups = new Set();

  for (const army of playableArmies) {
    if (army.role === "non_aligned" && army.group_id && !shownGroups.has(army.group_id)) {
      const label = new Option(army.group_name || `Group ${army.group_id}`, "");
      label.disabled = true;
      elements.army.add(label);
      shownGroups.add(army.group_id);
    }
    const indentLevel = army.role === "reinforcement"
      ? 2
      : Number(army.role === "sectorial" || army.role === "non_aligned");
    const indent = "\u00a0\u00a0\u00a0\u00a0".repeat(indentLevel);
    elements.army.add(new Option(
      `${indent}${army.name} (${number.format(army.unit_count)})`,
      armyFilterValue(army),
    ));
  }
  if (normalizedArmyFilter) writeLocation(true);
  elements.armyCount.textContent = number.format(playableArmies.length);
  elements.army.disabled = false;
  syncFilters();
}

function catalogFilterValue(item) {
  return item.slug || String(item.id);
}

function normalizeCatalogFilterState(items, stateKey) {
  const current = state[stateKey];
  if (!current || !/^\d+$/.test(current)) return false;
  const item = items.find((candidate) => (
    String(candidate.id) === current
    || candidate.source_ids?.some((sourceId) => String(sourceId) === current)
  ));
  if (!item) return false;
  const replacement = catalogFilterValue(item);
  if (replacement === current) return false;
  state[stateKey] = replacement;
  return true;
}

function normalizeUnitFilterState(items, stateKey) {
  const current = state[stateKey];
  if (!current || !/^\d+$/.test(current)) return false;
  const item = items.find((candidate) => String(candidate.id) === current);
  if (!item?.slug || item.slug === current) return false;
  state[stateKey] = item.slug;
  return true;
}

function populateCatalogFilter(element, items, label, displayName = (item) => item.name) {
  element.replaceChildren(new Option(`All ${label.toLowerCase()}`, ""));
  for (const item of items) {
    element.add(new Option(displayName(item), catalogFilterValue(item)));
  }
  element.disabled = false;
}

const availabilityLabels = {
  standard: "Standard units", mercs: "Mercenaries", specops: "Spec-Ops",
  teamops: "Team Operations", reinforcement: "Reinforcements",
};

function renderAvailabilityRows(element, categories, field, { includeStandard = false } = {}) {
  element.replaceChildren();
  for (const [key, label] of Object.entries(availabilityLabels)) {
    if (!includeStandard && key === "standard") continue;
    const count = categories[key]?.[field] || 0;
    if (!count) continue;
    const term = document.createElement("dt");
    term.textContent = label;
    const value = document.createElement("dd");
    value.textContent = number.format(count);
    element.append(term, value);
  }
}

function renderAvailabilitySummary(data) {
  const summary = data.availability || {
    shown: data.total, available: data.total, filtered: 0, categories: {},
  };
  elements.unitCount.textContent = `${number.format(summary.shown)} / ${number.format(summary.available)}`;
  renderAvailabilityRows(elements.unitCountShown, summary.categories, "shown", { includeStandard: true });
  renderAvailabilityRows(elements.unitCountFiltered, summary.categories, "filtered");
  elements.unitCountFilteredTotal.textContent = summary.filtered
    ? `${number.format(summary.filtered)} unique ${summary.filtered === 1 ? "unit is" : "units are"} currently filtered out.`
    : "No matching units are currently filtered out by availability.";
}


function renderDeclaredMembershipContext(data) {
  if (!state.declaredFactionId) {
    elements.declaredMembership.hidden = true;
    elements.declaredMembership.textContent = "";
    return;
  }
  const relationship = data.declared_faction;
  const label = relationship?.name || `Faction ${state.declaredFactionId}`;
  elements.declaredMembership.textContent = `Declared faction membership: ${label}. `
    + "This relationship is broader than concrete current Army-list availability.";
  elements.declaredMembership.hidden = false;
}

function renderUnits(data) {
  renderUnitRows(elements.list, data.items, { extended: state.extended });
  renderAvailabilitySummary(data);
  renderDeclaredMembershipContext(data);
  const hasFilters = Boolean(hasActiveFilters());
  if (!data.total) {
    elements.summary.textContent = "0 units found";
    elements.emptyTitle.textContent = hasFilters ? "No matching units" : "Your catalog is ready for data";
    elements.emptyMessage.textContent = hasFilters
      ? "Try another name or choose a different army."
      : "No units have been added to this database yet.";
    elements.emptyClear.hidden = !hasFilters;
    showPanel(elements.empty);
    return;
  }
  const first = data.offset + 1;
  const last = data.offset + data.items.length;
  const resultsSummary = `${number.format(first)}–${number.format(last)} of ${number.format(data.total)} units`;
  elements.summary.textContent = resultsSummary;
  const pageSummary = `Page ${number.format(Math.floor(data.offset / PAGE_SIZE) + 1)} of ${number.format(Math.ceil(data.total / PAGE_SIZE))}`;
  elements.pageSummary.forEach((summary) => {
    const range = document.createElement("span");
    range.className = "page-results-summary";
    range.textContent = resultsSummary;
    summary.replaceChildren(pageSummary, range);
  });
  elements.previous.forEach((button) => { button.disabled = data.offset === 0; });
  elements.next.forEach((button) => { button.disabled = data.offset + data.items.length >= data.total; });
  showPanel(elements.table);
  elements.pagination.forEach((pagination) => { pagination.hidden = false; });
}

async function load() {
  controller?.abort();
  controller = new AbortController();
  const signal = controller.signal;
  const currentRequest = ++requestNumber;
  showPanel(elements.loading);
  elements.unitCount.textContent = "—";
  elements.unitCountShown.replaceChildren();
  elements.unitCountFiltered.replaceChildren();
  elements.unitCountFilteredTotal.textContent = "";
  elements.summary.textContent = "Loading units…";
  try {
    if (!armiesLoaded) {
      const [armies, skills, equipment, weapons, unitFilters] = await Promise.all([
        getArmies(signal), getCatalogItems("skills", signal), getCatalogItems("equipment", signal), getCatalogItems("weapons", signal), getUnitFilters(signal),
      ]);
      if (currentRequest !== requestNumber) return;
      populateArmies(armies.items);
      const normalizedCatalogFilters = [
        normalizeCatalogFilterState(skills.items, "skillId"),
        normalizeCatalogFilterState(equipment.items, "equipmentId"),
        normalizeCatalogFilterState(weapons.items, "weaponId"),
        normalizeUnitFilterState(unitFilters.troop_types, "troopType"),
        normalizeUnitFilterState(unitFilters.classifications, "classification"),
        normalizeUnitFilterState(unitFilters.characteristics, "characteristic"),
      ].some(Boolean);
      populateCatalogFilter(elements.skill, skills.items, "Skills");
      populateCatalogFilter(elements.equipment, equipment.items, "Equipment");
      populateCatalogFilter(elements.weapon, weapons.items, "Weapons");
      populateCatalogFilter(
        elements.troopType, unitFilters.troop_types, "Troop types",
        (item) => item.display_name || item.name,
      );
      populateCatalogFilter(elements.classification, unitFilters.classifications, "Classifications");
      populateCatalogFilter(elements.characteristic, unitFilters.characteristics, "Characteristics");
      populateNumericFilter("ava", unitFilters.numeric?.ava);
      populateNumericFilter("points", unitFilters.numeric?.points);
      populateNumericFilter("swc", unitFilters.numeric?.swc);
      syncFilters();
      if (normalizedCatalogFilters) writeLocation(true);
      armiesLoaded = true;
    }
    const data = await getUnits(state, signal);
    if (currentRequest !== requestNumber) return;
    // Shared links can point beyond the end after the database is refreshed.
    if (data.total > 0 && state.offset >= data.total) {
      state.offset = Math.floor((data.total - 1) / PAGE_SIZE) * PAGE_SIZE;
      writeLocation(true);
      return load();
    }
    renderUnits(data);
  } catch (error) {
    if (signal.aborted || currentRequest !== requestNumber) return;
    elements.errorMessage.textContent = error instanceof TypeError
      ? "Could not connect to the database. Check your connection and try again."
      : error.message || "Something went wrong. Please try again.";
    elements.summary.textContent = "Unable to load units";
    showPanel(elements.error);
  }
}

function applyFilters() {
  clearTimeout(searchTimer);
  const next = {
    armyId: elements.army.value, search: elements.search.value.trim(),
    skillId: elements.skill.value, equipmentId: elements.equipment.value, weaponId: elements.weapon.value,
    troopType: elements.troopType.value, classification: elements.classification.value,
    characteristic: elements.characteristic.value,
    ava: avaExactFilterValue(elements.ava.value),
    avaMin: numericRangeStateValue(
      "ava", numericRangeControls.ava, elements.avaMin,
      numericRangeControls.ava.metadata?.min,
    ),
    avaMax: numericRangeStateValue(
      "ava", numericRangeControls.ava, elements.avaMax,
      numericRangeControls.ava.metadata?.max,
    ),
    points: integerFilterValue(elements.points.value),
    pointsMin: numericRangeStateValue(
      "points", numericRangeControls.points, elements.pointsMin,
      numericRangeControls.points.metadata?.min,
    ),
    pointsMax: numericRangeStateValue(
      "points", numericRangeControls.points, elements.pointsMax,
      numericRangeControls.points.metadata?.max,
    ),
    swc: swcExactFilterValue(elements.swc.value),
    swcMin: numericRangeStateValue(
      "swc", numericRangeControls.swc, elements.swcMin,
      numericRangeControls.swc.metadata?.min,
    ),
    swcMax: numericRangeStateValue(
      "swc", numericRangeControls.swc, elements.swcMax,
      numericRangeControls.swc.metadata?.max,
    ),
    extended: elements.extended.checked,
  };
  if (Object.entries(next).every(([key, value]) => state[key] === value)) return;
  state = {
    ...state, ...next, offset: 0, optionalUnitInvalid: false,
  };
  elements.clear.disabled = !hasActiveFilters();
  renderOptionalUnitContext();
  writeLocation();
  load();
}

function clearFilters() {
  clearTimeout(searchTimer);
  state = {
    ...state, armyId: "", declaredFactionId: "", search: "", offset: 0,
    skillId: "", equipmentId: "", weaponId: "",
    troopType: "", classification: "", characteristic: "",
    ava: "", avaMin: "", avaMax: "", points: "", pointsMin: "", pointsMax: "",
    swc: "", swcMin: "", swcMax: "",
    ...optionalUnitFilters(),
    optionalUnitSource: "preferences", optionalUnitInvalid: false,
  };
  syncFilters();
  renderOptionalUnitContext();
  writeLocation();
  load();
}

function changePage(direction) {
  clearTimeout(searchTimer);
  state.offset = Math.max(0, state.offset + direction * PAGE_SIZE);
  writeLocation();
  load();
}

function toggleSortOrder() {
  state = { ...state, descending: !state.descending, offset: 0 };
  updateSortButton();
  writeLocation();
  load();
}

function applyNumericExactFilter(control) {
  resetNumericRangeControl(control);
  applyFilters();
}

function resetNumericRangeAndApply(control) {
  resetNumericRangeControl(control);
  applyFilters();
}

elements.filters.addEventListener("submit", (event) => { event.preventDefault(); applyFilters(); });
elements.army.addEventListener("change", applyFilters);
for (const filter of [
  elements.skill, elements.equipment, elements.weapon,
  elements.troopType, elements.classification, elements.characteristic,
]) {
  filter.addEventListener("change", applyFilters);
}
for (const control of Object.values(numericRangeControls)) {
  control.exact.addEventListener("change", () => applyNumericExactFilter(control));
  control.reset.addEventListener("click", () => resetNumericRangeAndApply(control));
  for (const input of [control.minimum, control.maximum]) {
    input.addEventListener("input", () => updateNumericRangeFromInput(control, input));
    input.addEventListener("change", applyFilters);
    input.addEventListener("pointerdown", () => activateNumericRangeThumb(control, input));
    input.addEventListener("focus", () => activateNumericRangeThumb(control, input));
  }
}
elements.extended.addEventListener("change", applyFilters);
elements.search.addEventListener("input", () => {
  clearTimeout(searchTimer);
  elements.clear.disabled = !hasActiveFilters();
  searchTimer = setTimeout(applyFilters, 250);
});
elements.clear.addEventListener("click", clearFilters);
elements.emptyClear.addEventListener("click", clearFilters);
byId("retry").addEventListener("click", load);
elements.previous.forEach((button) => button.addEventListener("click", () => changePage(-1)));
elements.next.forEach((button) => button.addEventListener("click", () => changePage(1)));
elements.sortButton.addEventListener("click", toggleSortOrder);
function onPopstate() {
  clearTimeout(searchTimer);
  state = readLocation();
  syncFilters();
  renderOptionalUnitContext();
  load();
}

function onOptionalUnitsChange(event) {
  const filters = event.detail || optionalUnitFilters();
  if (OPTIONAL_UNIT_KEYS.every((key) => state[key] === filters[key])) {
    renderOptionalUnitContext();
    return;
  }
  state = {
    ...state, ...filters, offset: 0, optionalUnitSource: "preferences", optionalUnitInvalid: false,
  };
  syncFilters();
  renderOptionalUnitContext();
  writeLocation();
  load();
}

window.addEventListener("popstate", onPopstate);
window.addEventListener("optionalunitschange", onOptionalUnitsChange);
window.addEventListener("distanceunitchange", () => {
  if (state.extended) load();
});
document.addEventListener("infinity:beforenavigation", () => {
  clearTimeout(searchTimer);
  controller?.abort();
  window.removeEventListener("popstate", onPopstate);
  window.removeEventListener("optionalunitschange", onOptionalUnitsChange);
}, { once: true });

syncFilters();
renderOptionalUnitContext();
writeLocation(true);
load();
