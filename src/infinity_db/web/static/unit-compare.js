import { getUnit, getUnits } from "./api.js";
import { distanceUnit } from "./preferences.js";
import { formatMovement, formatProfileItem } from "./unit-presentation.js";
import { readShareState, shareStateHref, writeShareState } from "./share-state.js";
import { tableViewport, referenceLoadMessage, collectionLoadMessage } from "./view-components.js";

const pageController = new AbortController();
const signal = pageController.signal;
document.addEventListener("infinity:beforenavigation", () => pageController.abort(), { once: true });
const selectors = document.getElementById("comparison-selectors");
const results = document.getElementById("comparison-results");
const status = document.getElementById("comparison-status");
const differences = document.getElementById("comparison-differences");
const initial = readShareState("comparison");
const params = initial.params;
differences.checked = params.get("differences") === "1";
const identifierPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const allAvailability = { mercs: true, specops: true, teamops: true, reinforcement: true };

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text != null) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function field(title, control, id) {
  const wrapper = node("div", null, "field");
  control.id = id;
  const label = node("label", title);
  label.htmlFor = id;
  wrapper.append(label, control);
  return wrapper;
}

const unitKey = (unit) => String(unit.public_slug || unit.slug || unit.id);
const armyKey = (army) => JSON.stringify([army.public_slug || army.slug || army.id,
  [...(army.availability_flags || [])].sort()]);
const profileKey = (profile) => JSON.stringify([profile.group_id, profile.profile_id, profile.profile_identity]);
const loadoutKey = (loadout) => JSON.stringify([loadout.group_id, loadout.option_id, loadout.name]);
function selected(rows, key, value) {
  const matches = rows.filter((row) => key(row) === value);
  return matches.length === 1 ? matches[0] : null;
}

function fillOptions(control, rows, key, label, value, placeholder) {
  control.replaceChildren(new Option(placeholder, ""));
  for (const row of rows) {
    const option = new Option(label(row), key(row));
    if (rows.filter((candidate) => key(candidate) === option.value).length !== 1) {
      option.disabled = true;
      option.textContent += " (ambiguous)";
    }
    control.add(option);
  }
  if (value && !selected(rows, key, value) && !rows.some((row) => key(row) === value)) {
    const missing = new Option("Previously selected option is unavailable", value, true, true);
    missing.disabled = true;
    control.add(missing);
  }
  control.value = value || "";
  control.disabled = !rows.length && !value;
}

function armyLabel(army) {
  const badges = (army.availability_badges || []).map((badge) => badge.label);
  return [army.name, ...badges].join(" · ");
}

function slot(side, title) {
  const card = node("section", null, "surface surface--clipped comparison-selector");
  const heading = node("h2", title, "surface-titlebar surface-titlebar--ruled");
  const body = node("div", null, "surface-body");
  const form = node("form");
  const search = node("input");
  search.type = "search";
  search.maxLength = 200;
  search.placeholder = "Search Unit names…";
  search.autocomplete = "off";
  const submit = node("button", "Find Units", "button button-quiet");
  submit.type = "submit";
  form.append(field("Unit name", search, side + "-search"), submit);
  const matches = node("select");
  const matchField = field("Search results", matches, side + "-matches");
  matchField.hidden = true;
  const searchMessage = node("p", "", "detail-copy");
  searchMessage.setAttribute("role", "status");
  const message = node("p", "", "detail-copy");
  message.setAttribute("role", "status");
  const unitLink = node("a");
  unitLink.hidden = true;
  const clear = node("button", "Clear Unit", "button button-quiet");
  clear.type = "button";
  clear.disabled = true;
  const armySelect = node("select");
  const profileSelect = node("select");
  const loadoutSelect = node("select");
  body.append(form, matchField, searchMessage, message, unitLink, clear,
    field("Army", armySelect, side + "-army"),
    field("Profile", profileSelect, side + "-profile"),
    field("Loadout (optional)", loadoutSelect, side + "-loadout"));
  card.append(heading, body);
  selectors.append(card);
  const state = {
    side, unit: null, id: params.get(side) || "", armyId: params.get(side + "_army") || "",
    profileId: params.get(side + "_profile") || "", loadoutId: params.get(side + "_loadout") || "",
    army: null, profile: null, loadout: null, loading: false, request: 0, searchRequest: 0,
  };
  let searchTimer;
  let searchController;
  function cancelSearch() {
    clearTimeout(searchTimer);
    searchController?.abort();
    ++state.searchRequest;
    matchField.hidden = true;
    matches.replaceChildren();
    searchMessage.textContent = "";
  }
  signal.addEventListener("abort", cancelSearch, { once: true });
  function populate({ chooseDefaults = false } = {}) {
    const armies = (state.unit?.armies || []).filter((army) => army.presentation_visible !== false);
    if (chooseDefaults && !state.armyId) {
      const army = armies.find((item) => !(item.availability_flags || []).length) || armies[0];
      if (army) state.armyId = armyKey(army);
    }
    fillOptions(armySelect, armies, armyKey, armyLabel, state.armyId, "Select Army");
    state.army = selected(armies, armyKey, state.armyId);
    const profiles = state.army?.profiles || [];
    if (chooseDefaults && !state.profileId && profiles.length) state.profileId = profileKey(profiles[0]);
    fillOptions(profileSelect, profiles, profileKey, (profile) => profile.name || profile.display_name,
      state.profileId, "Select profile");
    state.profile = selected(profiles, profileKey, state.profileId);
    const loadouts = (state.army?.loadouts || []).filter((loadout) =>
      state.profile && loadout.group_id === state.profile.group_id);
    fillOptions(loadoutSelect, loadouts, loadoutKey,
      (loadout) => `${loadout.name} · ${show(loadout.points)} pts / ${show(loadout.swc)} SWC`,
      state.loadoutId, "Profile only");
    state.loadout = selected(loadouts, loadoutKey, state.loadoutId);
    unitLink.hidden = !state.unit;
    if (state.unit) {
      unitLink.textContent = state.unit.name + " — Unit details";
      unitLink.href = shareStateHref("/units/" + unitKey(state.unit), "unit",
        { army_id: state.army?.public_slug || state.army?.slug || state.army?.id });
    }
    clear.disabled = !state.id;
  }

  async function load(id, { restore = false } = {}) {
    const request = ++state.request;
    state.id = id;
    state.unit = null;
    state.loading = Boolean(id);
    if (!restore) state.armyId = state.profileId = state.loadoutId = "";
    populate();
    message.textContent = id ? "Loading Unit…" : "";
    update();
    if (!id) return;
    if (!identifierPattern.test(id) || id.length > 200) {
      state.loading = false;
      message.textContent = "Invalid Unit selection.";
      update();
      return;
    }
    try {
      const unit = await getUnit(id, {
        optionalFilters: allAvailability, includeHistory: false, view: "comparison",
      }, signal);
      if (signal.aborted || request !== state.request) return;
      state.unit = unit;
      state.id = unitKey(unit);
      populate({ chooseDefaults: !restore || !state.armyId });
      message.textContent = state.army && state.profile ? "" : "Select an available Army and profile.";
    } catch (error) {
      if (signal.aborted || request !== state.request) return;
      message.textContent = referenceLoadMessage(error, "Unit");
    } finally {
      if (!signal.aborted && request === state.request) {
        state.loading = false;
        update();
      }
    }
  }

  async function findUnits() {
    cancelSearch();
    const query = search.value.trim();
    if (!query || signal.aborted) return;
    const request = state.searchRequest;
    searchController = new AbortController();
    searchMessage.textContent = "Searching…";
    try {
      const data = await getUnits({ search: query, limit: 30, offset: 0, ...allAvailability },
        searchController.signal);
      if (signal.aborted || request !== state.searchRequest) return;
      fillOptions(matches, data.items, unitKey, (unit) => unit.name, "", "Select a Unit");
      matchField.hidden = false;
      searchMessage.textContent = data.total > 30
        ? "Showing the first 30 matches. Refine your search for more specific results."
        : data.items.length ? "" : "No matching Units.";
    } catch (error) {
      if (!signal.aborted && request === state.searchRequest && error.name !== "AbortError") {
        searchMessage.textContent = collectionLoadMessage(error, "Units");
      }
    }
  }
  function scheduleSearch(event) {
    cancelSearch();
    if (!event.isComposing && search.value.trim()) searchTimer = setTimeout(findUnits, 180);
  }
  search.addEventListener("input", scheduleSearch);
  search.addEventListener("compositionend", scheduleSearch);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    findUnits();
  });
  matches.addEventListener("change", () => { if (matches.value) load(matches.value); });
  clear.addEventListener("click", () => {
    cancelSearch();
    search.value = "";
    load("");
  });
  armySelect.addEventListener("change", () => {
    state.armyId = armySelect.value;
    state.profileId = state.loadoutId = "";
    populate({ chooseDefaults: Boolean(state.armyId) });
    update();
  });
  profileSelect.addEventListener("change", () => {
    state.profileId = profileSelect.value;
    state.loadoutId = "";
    populate();
    update();
  });
  loadoutSelect.addEventListener("change", () => {
    state.loadoutId = loadoutSelect.value;
    populate();
    update();
  });
  populate();
  return { state, load };
}

const show = (value) => value == null || value === "" ? "—" : String(value);
const slots = [slot("left", "Unit A"), slot("right", "Unit B")];

function listKey(items) {
  return JSON.stringify(items.map((item) => [
    item.slug || item.id || item.name, item.quantity ?? 1,
    (item.extras || []).map((extra) => extra.id ?? extra.name).sort(),
  ]).map(JSON.stringify).sort());
}

function itemList(items, catalog, label) {
  if (!items.length) return node("span", "—");
  const list = node("ul", null, "comparison-items");
  for (const item of items) {
    const text = formatProfileItem(item, label).label;
    const id = String(item.slug || item.id || "");
    const link = catalog && identifierPattern.test(id) ? node("a", text) : node("span", text);
    if (link.tagName === "A") link.href = "/" + catalog + "/" + encodeURIComponent(id);
    const li = node("li");
    li.append(link);
    list.append(li);
  }
  return list;
}

function render() {
  results.replaceChildren();
  if (slots.some(({ state }) => state.loading)) {
    status.textContent = "Loading selected Units…";
    return;
  }
  const states = slots.map(({ state }) => state);
  if (states.some((state) => state.unit && ((state.armyId && !state.army)
      || (state.profileId && !state.profile)))) {
    status.textContent = "A previously selected Army or profile is unavailable. Choose another option.";
    return;
  }
  if (states.some((state) => !state.profile)) {
    status.textContent = "Select an available Army profile on each side to compare.";
    return;
  }
  if (states.some((state) => state.loadoutId && !state.loadout)) {
    status.textContent = "A previously selected loadout is unavailable. Select another loadout or Profile only.";
    return;
  }
  status.textContent = "";
  const table = node("table", null, "data-table--compact data-table--reference comparison-table");
  const caption = node("caption", "Current Army profile and loadout comparison", "sr-only");
  const head = node("thead");
  const header = node("tr");
  for (const label of ["Attribute or capability", ...states.map((state, index) =>
    `${index === 0 ? "A" : "B"} · ${state.unit.name}`)]) {
    const th = node("th", label);
    th.scope = "col";
    header.append(th);
  }
  head.append(header);
  const body = node("tbody");
  let count = 0;
  function row(label, values, keys = values, renderValue = (value) => node("span", show(value)), always = false) {
    const differs = keys[0] !== keys[1];
    if (differences.checked && !differs && !always) return;
    const tr = node("tr");
    if (differs) tr.className = "comparison-different";
    const th = node("th", label);
    th.scope = "row";
    if (differs) th.append(node("span", " · differs", "comparison-difference-label"));
    tr.append(th);
    for (const value of values) {
      const td = node("td");
      td.append(renderValue(value));
      tr.append(td);
    }
    body.append(tr);
    if (differs && !always) count++;
  }
  row("Army", states.map((state) => armyLabel(state.army)), undefined, undefined, true);
  row("Profile", states.map((state) => state.profile.name), undefined, undefined, true);
  row("Loadout", states.map((state) => state.loadout?.name || "Profile only"), undefined, undefined, true);
  row("MOV", states.map(({ profile }) => formatMovement(profile.move_1, profile.move_2, distanceUnit())));
  for (const [label, key] of [
    ["CC", "cc"], ["BS", "bs"], ["PH", "ph"], ["WIP", "wip"], ["ARM", "arm"], ["BTS", "bts"],
  ]) row(label, states.map(({ profile }) => profile[key]));
  row("VITA / STR", states.map(({ profile }) =>
    profile.vitality == null ? "—" : `${show(profile.vitality)} ${profile.is_structure ? "STR" : "VITA"}`));
  for (const [label, key] of [["S", "silhouette"], ["AVA", "ava"], ["Troop type", "type_label"], ["Classification", "classification"]]) {
    row(label, states.map(({ profile }) => profile[key]));
  }
  row("Points", states.map(({ loadout }) => loadout?.points));
  row("SWC", states.map(({ loadout }) => loadout?.swc));
  for (const layer of ["profile", "loadout"]) {
    for (const [key, label] of [["skills", "Skills"], ["equipment", "Equipment"], ["weapons", "Weapons"]]) {
      const values = states.map((state) => state[layer]?.[key] || []);
      row(`${layer === "profile" ? "Profile" : "Loadout"} ${label}`, values, values.map(listKey),
        (items) => itemList(items, key, label));
    }
    for (const [key, label] of [["includes", "Includes"], ["peripherals", "Peripherals"]]) {
      const values = states.map((state) => state[layer]?.[key] || []);
      row(`${layer === "profile" ? "Profile" : "Loadout"} ${label}`, values,
        values.map((items) => JSON.stringify(items.map((item) =>
          [item.id ?? item.loadout_payload_id, item.name, item.quantity]).sort())),
        (items) => itemList(items, null, label));
    }
  }
  const characteristics = states.map(({ profile }) => profile.characteristics || []);
  row("Characteristics", characteristics, characteristics.map(listKey),
    (items) => itemList(items, null, "Characteristic"));
  table.append(caption, head, body);
  results.append(tableViewport(table));
  if (differences.checked && !count) status.textContent = "No differences in the displayed comparison fields.";
}

let initializing = true;
function update() {
  if (initializing || signal.aborted) return;
  const values = { differences: differences.checked ? "1" : "" };
  for (const { state } of slots) {
    values[state.side] = state.id;
    values[state.side + "_army"] = state.armyId;
    values[state.side + "_profile"] = state.profileId;
    values[state.side + "_loadout"] = state.loadoutId;
  }
  writeShareState("comparison", values, { replace: true });
  render();
}

differences.addEventListener("change", update);
window.addEventListener("distanceunitchange", render, { signal });
initializing = false;
Promise.all(slots.filter(({ state }) => state.id).map(({ state, load }) => load(state.id, { restore: true })))
  .then(() => {
    if (!signal.aborted) update();
  });
