import { getArmies } from "./api.js";
import { staticSymbolPath } from "./unit-symbols.js";

const number = new Intl.NumberFormat();
const byId = (id) => document.getElementById(id);
const elements = {
  count: byId("army-overview-count"),
  results: byId("army-overview-results"),
  loading: byId("army-overview-loading"),
  error: byId("army-overview-error"),
  errorMessage: byId("army-overview-error-message"),
  empty: byId("army-overview-empty"),
  groups: byId("army-overview-groups"),
};
const controller = new AbortController();

function show(panel) {
  for (const element of [elements.loading, elements.error, elements.empty, elements.groups]) {
    element.hidden = element !== panel;
  }
  elements.results.setAttribute("aria-busy", String(panel === elements.loading));
}

function armyValue(army) {
  return army.public_slug || army.slug || String(army.id);
}

function roleLabel(army) {
  if (army.role === "main") return "Main army";
  if (army.role === "sectorial") return "Sectorial";
  if (army.role === "non_aligned") return "Non-Aligned Army";
  if (army.role === "reinforcement") return "Reinforcements";
  return "Army";
}

function statusBadge(label, modifier) {
  const badge = document.createElement("span");
  badge.className = `status-badge status-badge--${modifier}`;
  badge.textContent = label;
  return badge;
}

function armyStatuses(army) {
  const statuses = document.createElement("div");
  statuses.className = "detail-badges army-overview-statuses";
  if (army.out_of_catalog) statuses.append(statusBadge("Out of catalog", "warning"));
  if (army.legacy) {
    statuses.append(
      statusBadge("Legacy", "muted"),
      statusBadge("Not playable in N5", "muted"),
    );
  }
  return statuses;
}

function renderArmy(army) {
  const article = document.createElement("article");
  article.className = "surface surface--subtle surface--raised army-overview-card";

  const heading = document.createElement("div");
  heading.className = "army-overview-card-heading";
  if (army.symbol_path) {
    const symbol = document.createElement("img");
    symbol.className = "army-overview-symbol";
    symbol.src = staticSymbolPath(army.symbol_path);
    symbol.alt = "";
    heading.append(symbol);
  }
  const identity = document.createElement("div");
  identity.className = "army-overview-card-identity";
  const kind = document.createElement("p");
  kind.className = "eyebrow";
  kind.textContent = roleLabel(army);
  const title = document.createElement("h3");
  title.textContent = army.name;
  identity.append(kind, title);
  const statuses = armyStatuses(army);
  if (statuses.childElementCount) identity.append(statuses);
  heading.append(identity);

  const description = document.createElement("p");
  description.className = "detail-copy army-overview-description";
  description.textContent = army.overview_description || "Browse this Army in Unit Explorer.";

  const footer = document.createElement("div");
  footer.className = "army-overview-card-footer";
  if (army.playable === false) {
    const note = document.createElement("span");
    note.className = "detail-source";
    note.textContent = "Historical reference only";
    footer.append(note);
  } else {
    const count = document.createElement("span");
    count.className = "detail-badge";
    count.textContent = `${number.format(army.unit_count || 0)} units`;
    const link = document.createElement("a");
    link.className = "button button-primary";
    link.href = `/units?${new URLSearchParams({ army_id: armyValue(army) })}`;
    link.textContent = "Browse units";
    footer.append(count, link);
  }

  article.append(heading, description, footer);
  return article;
}

function render(items) {
  const playable = items.filter((army) => army.playable !== false);
  const legacy = items.filter((army) => army.legacy);
  const visible = items.filter((army) => army.playable !== false || army.legacy);
  elements.count.textContent = legacy.length
    ? `${number.format(playable.length)} playable · ${number.format(legacy.length)} legacy`
    : `${number.format(playable.length)} playable`;
  if (!visible.length) return show(elements.empty);

  const groups = new Map();
  for (const army of visible) {
    const group = army.overview_group || { id: army.id, name: army.name };
    if (!groups.has(group.id)) groups.set(group.id, { ...group, armies: [] });
    groups.get(group.id).armies.push(army);
  }

  const fragment = document.createDocumentFragment();
  for (const group of groups.values()) {
    const section = document.createElement("section");
    section.className = "army-overview-group";
    const heading = document.createElement("h3");
    heading.className = "detail-heading";
    heading.textContent = group.name;
    const grid = document.createElement("div");
    grid.className = "army-overview-grid";
    grid.replaceChildren(...group.armies.map(renderArmy));
    section.append(heading, grid);
    fragment.append(section);
  }
  elements.groups.replaceChildren(fragment);
  show(elements.groups);
}

async function initialize() {
  show(elements.loading);
  try {
    const payload = await getArmies(controller.signal);
    render(payload.items || []);
  } catch (error) {
    if (error.name === "AbortError") return;
    elements.errorMessage.textContent = error.message || "Could not load the Army overview.";
    show(elements.error);
  }
}

document.addEventListener("infinity:beforenavigation", () => controller.abort(), { once: true });
initialize();
