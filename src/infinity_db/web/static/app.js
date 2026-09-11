import { getArmies, getUnits } from "./api.js";
import { initializeDistanceUnitToggle } from "./preferences.js";
import { renderUnitRows } from "./unit-list.js";

const PAGE_SIZE = 50;
const number = new Intl.NumberFormat();
const byId = (id) => document.getElementById(id);
const elements = {
  filters: byId("filters"), army: byId("army-filter"), search: byId("unit-search"),
  mercs: byId("mercs-filter"), specops: byId("specops-filter"), teamops: byId("teamops-filter"),
  reinforcement: byId("reinforcement-filter"),
  clear: byId("clear-filters"), unitCount: byId("unit-count"), armyCount: byId("army-count"),
  summary: byId("results-summary"), results: byId("results"), loading: byId("loading-state"),
  error: byId("error-state"), errorMessage: byId("error-message"), empty: byId("empty-state"),
  emptyTitle: byId("empty-title"), emptyMessage: byId("empty-message"), emptyClear: byId("empty-clear"),
  table: byId("table-container"), list: byId("unit-list"), pagination: byId("pagination"),
  pageSummary: byId("page-summary"), previous: byId("previous-page"), next: byId("next-page"),
};

let state = readLocation();
let armiesLoaded = false;
let requestNumber = 0;
let controller;
let searchTimer;

function hasActiveFilters() {
  return state.armyId || state.search || state.mercs || !state.specops || state.teamops || state.reinforcement;
}

function readLocation() {
  const params = new URLSearchParams(window.location.search);
  const offset = Number(params.get("offset") || 0);
  const armyId = params.get("army_id") || "";
  return {
    armyId: /^\d+$/.test(armyId) ? armyId : "",
    search: (params.get("search") || "").trim().slice(0, 200),
    mercs: params.get("mercs") === "1",
    specops: params.get("specops") !== "0",
    teamops: params.get("teamops") === "1",
    reinforcement: params.get("reinforcement") === "1",
    offset: Number.isSafeInteger(offset) && offset >= 0 ? Math.floor(offset / PAGE_SIZE) * PAGE_SIZE : 0,
    limit: PAGE_SIZE,
  };
}

function writeLocation(replace = false) {
  const url = new URL(window.location.href);
  for (const key of ["army_id", "search", "offset", "mercs", "specops", "teamops", "reinforcement"]) url.searchParams.delete(key);
  if (state.armyId) url.searchParams.set("army_id", state.armyId);
  if (state.search) url.searchParams.set("search", state.search);
  if (state.offset) url.searchParams.set("offset", String(state.offset));
  if (state.mercs) url.searchParams.set("mercs", "1");
  if (!state.specops) url.searchParams.set("specops", "0");
  if (state.teamops) url.searchParams.set("teamops", "1");
  if (state.reinforcement) url.searchParams.set("reinforcement", "1");
  if (url.href !== window.location.href) {
    window.history[replace ? "replaceState" : "pushState"](null, "", url);
  }
}

function syncFilters() {
  elements.army.value = state.armyId;
  elements.search.value = state.search;
  elements.mercs.checked = state.mercs;
  elements.specops.checked = state.specops;
  elements.teamops.checked = state.teamops;
  elements.reinforcement.checked = state.reinforcement;
  elements.clear.disabled = !hasActiveFilters();
}

function showPanel(panel) {
  for (const element of [elements.loading, elements.error, elements.empty, elements.table]) {
    element.hidden = element !== panel;
  }
  const loading = panel === elements.loading;
  elements.results.setAttribute("aria-busy", String(loading));
  if (panel !== elements.table) elements.pagination.hidden = true;
}

function populateArmies(armies) {
  // Keep source strings out of HTML so upstream data is always treated as text.
  elements.army.replaceChildren(new Option("All armies", ""));
  const mainArmyIds = new Map();
  for (const army of armies) {
    const group = Math.floor(Number(army.id) / 100);
    if (!mainArmyIds.has(group)) mainArmyIds.set(group, army.id);
  }
  for (const army of armies) {
    const group = Math.floor(Number(army.id) / 100);
    const isSectorial = army.kind === "army" && mainArmyIds.get(group) !== army.id;
    const indentLevel = army.kind === "reinforcement" ? 2 : Number(isSectorial);
    const indent = "\u00a0\u00a0\u00a0\u00a0".repeat(indentLevel);
    elements.army.add(new Option(`${indent}${army.name} (${number.format(army.unit_count)})`, String(army.id)));
  }
  if (state.armyId && !armies.some((army) => String(army.id) === state.armyId)) {
    state.armyId = "";
    state.offset = 0;
    writeLocation(true);
  }
  elements.armyCount.textContent = number.format(armies.length);
  elements.army.disabled = false;
  syncFilters();
}

function renderUnits(data) {
  renderUnitRows(elements.list, data.items);
  elements.unitCount.textContent = number.format(data.total);
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
  elements.summary.textContent = `${number.format(first)}–${number.format(last)} of ${number.format(data.total)} units`;
  elements.pageSummary.textContent = `Page ${number.format(Math.floor(data.offset / PAGE_SIZE) + 1)} of ${number.format(Math.ceil(data.total / PAGE_SIZE))}`;
  elements.previous.disabled = data.offset === 0;
  elements.next.disabled = data.offset + data.items.length >= data.total;
  showPanel(elements.table);
  elements.pagination.hidden = false;
}

async function load() {
  controller?.abort();
  controller = new AbortController();
  const signal = controller.signal;
  const currentRequest = ++requestNumber;
  showPanel(elements.loading);
  elements.unitCount.textContent = "—";
  elements.summary.textContent = "Loading units…";
  try {
    if (!armiesLoaded) {
      const data = await getArmies(signal);
      if (currentRequest !== requestNumber) return;
      populateArmies(data.items);
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
    mercs: elements.mercs.checked, specops: elements.specops.checked, teamops: elements.teamops.checked,
    reinforcement: elements.reinforcement.checked,
  };
  if (Object.entries(next).every(([key, value]) => state[key] === value)) return;
  state = { ...state, ...next, offset: 0 };
  elements.clear.disabled = !hasActiveFilters();
  writeLocation();
  load();
}

function clearFilters() {
  clearTimeout(searchTimer);
  state = {
    ...state, armyId: "", search: "", mercs: false, specops: true, teamops: false,
    reinforcement: false, offset: 0,
  };
  syncFilters();
  writeLocation();
  load();
}

function changePage(direction) {
  clearTimeout(searchTimer);
  state.offset = Math.max(0, state.offset + direction * PAGE_SIZE);
  writeLocation();
  load();
}

elements.filters.addEventListener("submit", (event) => { event.preventDefault(); applyFilters(); });
elements.army.addEventListener("change", applyFilters);
for (const filter of [elements.mercs, elements.specops, elements.teamops, elements.reinforcement]) {
  filter.addEventListener("change", applyFilters);
}
elements.search.addEventListener("input", () => {
  clearTimeout(searchTimer);
  elements.clear.disabled = !hasActiveFilters();
  searchTimer = setTimeout(applyFilters, 250);
});
elements.clear.addEventListener("click", clearFilters);
elements.emptyClear.addEventListener("click", clearFilters);
byId("retry").addEventListener("click", load);
elements.previous.addEventListener("click", () => changePage(-1));
elements.next.addEventListener("click", () => changePage(1));
window.addEventListener("popstate", () => {
  clearTimeout(searchTimer);
  state = readLocation();
  syncFilters();
  load();
});

initializeDistanceUnitToggle();
syncFilters();
writeLocation(true);
load();
