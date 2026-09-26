import { getFireteamArmies, getFireteamChart } from "./api.js";

const byId = (id) => document.getElementById(id);
const elements = {
  army: byId("fireteam-army"),
  count: byId("fireteam-count"),
  results: byId("fireteam-results"),
  loading: byId("fireteam-loading"),
  error: byId("fireteam-error"),
  errorMessage: byId("fireteam-error-message"),
  empty: byId("fireteam-empty"),
  content: byId("fireteam-content"),
  chartName: byId("fireteam-chart-name"),
  description: byId("fireteam-chart-description"),
  limits: byId("fireteam-chart-limits"),
  source: byId("fireteam-chart-source"),
  sourceDetail: byId("fireteam-chart-source-detail"),
  list: byId("fireteam-list"),
};

let armies = [];
let requestController = null;

function show(panel) {
  for (const element of [elements.loading, elements.error, elements.empty, elements.content]) {
    element.hidden = element !== panel;
  }
  elements.results.setAttribute("aria-busy", String(panel === elements.loading));
}

function armyValue(army) {
  return army.public_slug || army.slug || String(army.id);
}

function currentArmyValue() {
  return new URLSearchParams(window.location.search).get("army") || "";
}

function writeArmyLocation(value, { replace = false } = {}) {
  const url = new URL(window.location.href);
  if (value) url.searchParams.set("army", value);
  else url.searchParams.delete("army");
  const method = replace ? "replaceState" : "pushState";
  history[method](null, "", `${url.pathname}${url.search}`);
}

function populateArmies(items) {
  armies = items;
  elements.army.replaceChildren();
  for (const army of armies) {
    const count = Number(army.fireteam_count || 0);
    elements.army.add(new Option(
      `${army.name}${count ? ` (${count})` : ""}`,
      armyValue(army),
    ));
  }
  elements.army.disabled = armies.length === 0;
}

function normalizeSelection() {
  if (!armies.length) return "";
  const requested = currentArmyValue();
  const selected = armies.find((army) => (
    armyValue(army) === requested || String(army.id) === requested
  )) || armies[0];
  const value = armyValue(selected);
  elements.army.value = value;
  if (requested !== value) writeArmyLocation(value, { replace: true });
  return value;
}

function badge(text, className = "skill-category-badge skill-category-badge--unclassified") {
  const element = document.createElement("span");
  element.className = className;
  element.textContent = text;
  return element;
}

function memberRequirement(member) {
  const parts = [];
  if (member.required) parts.push("Required choice");
  const min = member.min_count;
  const max = member.max_count;
  if (min != null && max != null && min === max) parts.push(`Exactly ${min}`);
  else {
    if (min != null) parts.push(`Min ${min}`);
    if (max != null) parts.push(`Max ${max}`);
  }
  return parts;
}

function memberName(member) {
  if (!member.unit) return document.createTextNode(member.name || "Unnamed member");
  const link = document.createElement("a");
  link.href = `/units/${member.unit.slug || member.unit.id}`;
  link.textContent = member.name || member.unit.name;
  return link;
}

function appendMemberDetails(cell, member) {
  const requirements = memberRequirement(member);
  const labels = member.equivalence_labels || [];
  if (requirements.length) {
    const group = document.createElement("div");
    group.className = "detail-badges";
    for (const requirement of requirements) group.append(badge(requirement));
    cell.append(group);
  }
  if (labels.length) {
    const countsAs = document.createElement("span");
    countsAs.className = "fireteam-member-note";
    countsAs.textContent = `Counts as: ${labels.join(", ")}`;
    cell.append(countsAs);
  }
  if (!requirements.length && !labels.length) cell.textContent = "—";
}

function appendFtoDetails(cell, member) {
  const loadouts = member.loadouts || [];
  if (!member.fto_marker && !loadouts.length) {
    cell.textContent = "—";
    return;
  }
  if (member.fto_marker) {
    const marker = member.fto_marker === "generic" ? "FTO" : `FTO-${member.fto_marker}`;
    cell.append(badge(marker));
  }
  if (loadouts.length) {
    const list = document.createElement("ul");
    list.className = "fireteam-loadout-list";
    for (const loadout of loadouts) {
      const item = document.createElement("li");
      item.textContent = loadout.name;
      list.append(item);
    }
    cell.append(list);
  }
}

function renderTeam(team) {
  const article = document.createElement("article");
  article.className = "fireteam-card";
  const header = document.createElement("header");
  header.className = "fireteam-card-header";
  const title = document.createElement("h3");
  title.textContent = team.name || `Fireteam ${team.id}`;
  const typeBadges = document.createElement("div");
  typeBadges.className = "detail-badges";
  if (team.is_wildcard) typeBadges.append(badge("Wildcard"));
  for (const type of team.types || []) typeBadges.append(badge(type));
  header.append(title, typeBadges);
  article.append(header);

  if (team.observation) {
    const observation = document.createElement("p");
    observation.className = "fireteam-observation";
    observation.textContent = team.observation;
    article.append(observation);
  }

  if (!(team.members || []).length) {
    const empty = document.createElement("p");
    empty.className = "detail-copy";
    empty.textContent = "No member rows are defined for this chart entry.";
    article.append(empty);
    return article;
  }

  const tableContainer = document.createElement("div");
  tableContainer.className = "table-container fireteam-member-table";
  const table = document.createElement("table");
  const caption = document.createElement("caption");
  caption.className = "sr-only";
  caption.textContent = `${team.name || "Fireteam"} members`;
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const heading of ["Member", "Requirements", "FTO profiles", "Notes"]) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = heading;
    headRow.append(cell);
  }
  head.append(headRow);
  const body = document.createElement("tbody");
  for (const member of team.members) {
    const row = document.createElement("tr");
    const name = document.createElement("th");
    name.scope = "row";
    name.append(memberName(member));
    const requirements = document.createElement("td");
    appendMemberDetails(requirements, member);
    const fto = document.createElement("td");
    appendFtoDetails(fto, member);
    const note = document.createElement("td");
    note.textContent = member.comment || "—";
    const developer = document.createElement("span");
    developer.className = "developer-only fireteam-member-developer";
    developer.textContent = `Resolution: ${member.resolution}; source member #${member.source_member_id}`;
    note.append(developer);
    row.append(name, requirements, fto, note);
    body.append(row);
  }
  table.append(caption, head, body);
  tableContainer.append(table);
  article.append(tableContainer);
  return article;
}

function renderChart(chart) {
  elements.chartName.textContent = chart.army.name;
  elements.description.textContent = chart.description || "";
  elements.description.hidden = !chart.description;
  elements.limits.replaceChildren();
  for (const limit of chart.limits || []) {
    const label = limit.max_count === 0
      ? `${limit.type}: unavailable`
      : `${limit.type}: max ${limit.max_count}`;
    elements.limits.append(badge(label));
  }
  const sourceKind = chart.source.kind
    ? chart.source.kind.replaceAll("_", " ")
    : "Army";
  elements.source.textContent = `Authoritative ${sourceKind} chart from the current Army snapshot.`;
  const sourceDetails = [`Source Army #${chart.source.army_id}`];
  if (chart.source.file) sourceDetails.push(chart.source.file);
  if (chart.source.sha256) sourceDetails.push(chart.source.sha256);
  elements.sourceDetail.textContent = sourceDetails.join(" · ");
  elements.list.replaceChildren(...(chart.teams || []).map(renderTeam));
  elements.count.textContent = `${(chart.teams || []).length} chart entries`;
  show((chart.teams || []).length || (chart.limits || []).length || chart.description
    ? elements.content
    : elements.empty);
}

async function loadChart(value) {
  if (!value) return show(elements.empty);
  requestController?.abort();
  requestController = new AbortController();
  show(elements.loading);
  try {
    renderChart(await getFireteamChart(value, requestController.signal));
  } catch (error) {
    if (error.name === "AbortError") return;
    elements.errorMessage.textContent = error.message || "Could not load the Fireteam chart.";
    show(elements.error);
  }
}

async function initialize() {
  show(elements.loading);
  try {
    const payload = await getFireteamArmies();
    populateArmies(payload.items || []);
    if (!armies.length) {
      elements.count.textContent = "0 armies";
      return show(elements.empty);
    }
    await loadChart(normalizeSelection());
  } catch (error) {
    elements.errorMessage.textContent = error.message || "Could not load Fireteam Armies.";
    show(elements.error);
  }
}

elements.army.addEventListener("change", () => {
  const value = elements.army.value;
  writeArmyLocation(value);
  loadChart(value);
});
window.addEventListener("popstate", () => loadChart(normalizeSelection()));

initialize();
